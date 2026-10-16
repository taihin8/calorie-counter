import flet as ft
from datetime import date, datetime, timedelta
from calendar import monthrange
from database import (add_food_entry, get_daily_food, get_daily_calories,
                      add_note, get_notes, delete_note, update_note,
                      delete_food_entry, update_food_entry, get_entry_dates,
                      get_calorie_goal, set_calorie_goal, get_goal_progress,
                      get_theme, set_theme)
from services.speech import recognize_async, parse_food_text
from services.themes import THEMES, apply_theme

GREEN = ft.Colors.GREEN_400
GREY = ft.Colors.GREY_300

def _log_error(context, ex):
    """Пишет ошибку в instance/crash.log, чтобы не терять причину."""
    import os, traceback
    path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'crash.log')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f"[{context}] {ex}\n{traceback.format_exc()}\n")

def diary_screen(page: ft.Page):
    user = page.session.store.get("user")
    if not user:
        from screens.login import login_screen
        login_screen(page)
        return

    page.clean()
    page.window.width = 480
    page.window.height = 800
    apply_theme(page, get_theme(user['id']))
    selected_date = str(date.today())
    total = ft.Text("0 ккал", size=22, weight=ft.FontWeight.BOLD)
    date_text = ft.Text(selected_date, size=16, weight=ft.FontWeight.BOLD)
    food_list = ft.Column(spacing=0)
    note_input = ft.TextField(label="Новая заметка", width=280, multiline=True)
    notes_list = ft.Column(spacing=0)

    # ---------- Цель калорий ----------
    goal_text = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    goal_left = ft.Text("", size=13)
    goal_bar = ft.ProgressBar(value=0, bar_height=10)

    def refresh_goal():
        goal, eaten, left = get_goal_progress(user['id'], selected_date)
        goal_text.value = f"🎯 Цель: {goal:.0f} ккал"
        # прогресс: не выше 1.0, но при переборе показываем полный + красный
        ratio = min(eaten / goal, 1.0) if goal else 0
        goal_bar.value = ratio
        if left >= 0:
            goal_left.value = f"Съедено {eaten:.0f} · осталось {left:.0f} ккал"
            goal_left.color = ft.Colors.GREEN
            goal_bar.color = ft.Colors.GREEN
        else:
            goal_left.value = f"Перебор на {-left:.0f} ккал! 🚨"
            goal_left.color = ft.Colors.RED
            goal_bar.color = ft.Colors.RED
        page.update()

    def edit_goal(e):
        field = ft.TextField(label="Цель, ккал в день",
                             value=str(int(get_calorie_goal(user['id']))),
                             keyboard_type=ft.KeyboardType.NUMBER, autofocus=True)

        def save(dlg):
            page.pop_dialog()
            if field.value:
                try:
                    set_calorie_goal(user['id'], float(field.value.replace(',', '.')))
                    refresh_goal()
                except ValueError:
                    pass

        dialog = ft.AlertDialog(
            title=ft.Text("Дневная цель калорий"),
            content=field,
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton("Сохранить", on_click=lambda e: save(dialog)),
            ]
        )
        page.show_dialog(dialog)

    # ---------- Календарь с подсветкой ----------
    def build_calendar_dialog():
        """Месячный календарь: зелёные даты = есть записи."""
        cal_month = datetime.now().replace(day=1)
        marked = set(get_entry_dates(user['id']))

        def on_pick(d):
            nonlocal selected_date
            selected_date = d.strftime("%Y-%m-%d")
            refresh()
            page.pop_dialog()

        def render():
            header = ft.Row([
                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: change_month(-1)),
                ft.Text(cal_month.strftime("%B %Y"), size=16, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: change_month(1)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            weekdays = ft.Row([ft.Text(w, size=12, color=ft.Colors.GREY, expand=True, text_align=ft.TextAlign.CENTER)
                               for w in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])

            first = cal_month.weekday()  # 0 = понедельник
            days_in_month = monthrange(cal_month.year, cal_month.month)[1]
            today = date.today()

            cells = []
            # пустые ячейки до первого дня
            cells += [ft.Container(width=34, height=34) for _ in range(first)]
            for day in range(1, days_in_month + 1):
                d = date(cal_month.year, cal_month.month, day)
                is_marked = d.strftime("%Y-%m-%d") in marked
                is_today = d == today
                bg = GREEN if is_marked else (ft.Colors.BLUE_50 if is_today else None)
                cells.append(
                    ft.Container(
                        width=34, height=34, bgcolor=bg, border_radius=17,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(str(day), size=11,
                                        weight=ft.FontWeight.BOLD if is_today else ft.FontWeight.NORMAL),
                        on_click=lambda e, dd=d: on_pick(dd),
                    )
                )

            weeks = [cells[i:i+7] for i in range(0, len(cells), 7)]
            body = ft.Column([ft.Row(week, spacing=2) for week in weeks], spacing=3)

            return ft.Column([header, ft.Divider(height=10), weekdays, body])

        def change_month(delta):
            nonlocal cal_month
            cal_month = (cal_month.replace(day=28) + timedelta(days=delta*7)).replace(day=1)
            dialog.content = render()
            page.update()

        dialog = ft.AlertDialog(title=ft.Text("Календарь"), content=render(),
                                actions=[ft.TextButton("Закрыть", on_click=lambda e: page.pop_dialog())])
        return dialog

    def open_calendar(e):
        page.show_dialog(build_calendar_dialog())

    # ---------- Темы ----------
    def open_themes(e):
        current = get_theme(user['id'])
        chips = ft.Row(wrap=True, spacing=4, run_spacing=4)

        def choose(name):
            try:
                set_theme(user['id'], name)
                page.pop_dialog()
                apply_theme(page, name)
            except Exception as ex:
                # не даём приложению упасть на смене темы
                import traceback
                _log_error("theme", ex)

        for name, (label, _, _) in THEMES.items():
            chips.controls.append(
                ft.Chip(label=ft.Text(label), selected=(name == current),
                        on_click=lambda e, n=name: choose(n))
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Тема оформления"),
            content=chips,
            actions=[ft.TextButton("Закрыть", on_click=lambda e: page.pop_dialog())],
        )
        page.show_dialog(dialog)

    # ---------- Продукты ----------
    def refresh():
        entries = get_daily_food(user['id'], selected_date)
        food_list.controls.clear()
        for en in entries:
            food_list.controls.append(
                ft.Row([
                    ft.Text(f"{en['product_name']} — {en['calories']:.0f} ккал/100г ({en['grams']:.0f} г)",
                            size=13, expand=True),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=14, width=26, height=26, padding=0,
                                  tooltip="Изменить",
                                  on_click=lambda _, eid=en['id'], n=en['product_name'],
                                  c=en['calories'], g=en['grams']: edit_food_dialog(eid, n, c, g)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14, width=26, height=26, padding=0,
                                  tooltip="Удалить",
                                  on_click=lambda _, eid=en['id']: delete_food(eid)),
                ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )
        cal = get_daily_calories(user['id'], selected_date)
        total.value = f"{cal:.0f} ккал"
        date_text.value = selected_date
        page.update()

    def delete_food(eid):
        delete_food_entry(eid)
        refresh()

    def food_dialog(entry_id=None, name_val="", cal_val="", grams_val="100"):
        name = ft.TextField(label="Название", value=name_val, autofocus=entry_id is None)
        cal_field = ft.TextField(label="Калорий на 100г", value=str(cal_val) if cal_val != "" else "",
                                 keyboard_type=ft.KeyboardType.NUMBER)
        grams_field = ft.TextField(label="Грамм", value=str(grams_val) if grams_val != "" else "100",
                                   keyboard_type=ft.KeyboardType.NUMBER)
        status = ft.Text("", size=11, color=GREEN)

        # подсветка при записи
        def set_recording(active):
            name.fill_color = ft.Colors.GREEN_50 if active else None
            name.label = "🎙 Говорите..." if active else "Название"

        def do_search(e):
            """Ищет калории по названию в базе"""
            from services.food_db import guess_calories
            cal = guess_calories(name.value)
            if cal:
                cal_field.value = str(cal).replace('.', ',')
                status.value = f"Найдено: {cal:.0f} ккал/100г"
                status.color = GREEN
            else:
                status.value = "Не нашёл в базе, впишите вручную"
                status.color = ft.Colors.ORANGE
            page.update()

        def voice(e):
            def on_result(text):
                set_recording(False)
                if text:
                    n, c, g = parse_food_text(text)
                    if n:
                        name.value = n
                    if c:
                        cal_field.value = str(c).replace('.', ',')
                    if g:
                        grams_field.value = str(g).replace('.', ',')
                    # если калорий не назвали голосом — попробуем угадать по названию
                    if n and not c:
                        from services.food_db import guess_calories
                        cal = guess_calories(n)
                        if cal:
                            cal_field.value = str(cal).replace('.', ',')
                            status.value = f"Калории из базы: {cal:.0f}/100г"
                            status.color = GREEN
                page.update()

            set_recording(True)
            status.value = ""
            page.update()
            # слушаем микрофон
            recognize_async(page.run_thread, on_result)

        mic_btn = ft.IconButton(ft.Icons.MIC, tooltip="Надиктовать продукт", on_click=voice)
        find_btn = ft.TextButton("Найти калории", on_click=do_search)

        def save(dlg):
            page.pop_dialog()
            if name.value and cal_field.value:
                cal = float(cal_field.value.replace(',', '.'))
                gr = float(grams_field.value.replace(',', '.') or 100)
                if entry_id is None:
                    add_food_entry(user['id'], name.value, cal, gr, selected_date)
                else:
                    update_food_entry(entry_id, name.value, cal, gr)
                refresh()

        dialog = ft.AlertDialog(
            title=ft.Text("Продукт"),
            content=ft.Column([
                ft.Row([name, mic_btn], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                find_btn, cal_field, grams_field, status,
            ]),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton("Сохранить", on_click=lambda e: save(dialog)),
            ]
        )
        page.show_dialog(dialog)

    def add_food(e):
        food_dialog()

    def edit_food_dialog(eid, n, c, g):
        food_dialog(entry_id=eid, name_val=n, cal_val=c, grams_val=g)

    # ---------- Заметки ----------
    def refresh_notes():
        notes = get_notes(user['id'])
        notes_list.controls.clear()
        for n in notes[:20]:
            notes_list.controls.append(
                ft.Row([
                    ft.Text(f"[{n['date']}] {n['text'][:45]}", size=11, expand=True),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=14, width=26, height=26, padding=0,
                                  on_click=lambda _, nid=n['id'], txt=n['text']: edit_note(nid, txt)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14, width=26, height=26, padding=0,
                                  on_click=lambda _, nid=n['id']: delete_and_refresh(nid)),
                ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )
        page.update()

    def edit_note(nid, old_text):
        field = ft.TextField(label="Заметка", value=old_text, multiline=True, autofocus=True)

        def save(dlg):
            page.pop_dialog()
            if field.value:
                update_note(nid, field.value)
                refresh_notes()

        dialog = ft.AlertDialog(
            title=ft.Text("Редактировать заметку"),
            content=field,
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton("Сохранить", on_click=lambda e: save(dialog)),
            ]
        )
        page.show_dialog(dialog)

    def delete_and_refresh(nid):
        delete_note(nid)
        refresh_notes()

    def save_note(e):
        if note_input.value:
            add_note(user['id'], note_input.value, selected_date)
            note_input.value = ""
            refresh_notes()

    # ---------- Голосовой ввод заметок ----------
    def voice_input(e):
        def on_result(text):
            note_input.fill_color = None
            note_input.label = "Новая заметка"
            if text:
                note_input.value = (note_input.value or "") + (" " + text if note_input.value else text)
            page.update()

        note_input.fill_color = ft.Colors.GREEN_50
        note_input.label = "🎙 Слушаю, говорите..."
        page.update()
        recognize_async(page.run_thread, on_result)

    refresh()
    refresh_notes()
    refresh_goal()

    page.add(
        ft.Column([
            ft.Row([
                ft.Text(f"👤 {user['username']}", size=14, color=ft.Colors.GREY),
                ft.Row([
                    ft.TextButton("Сменить", tooltip="Сменить пользователя",
                                  on_click=lambda e: switch_user(page)),
                    ft.TextButton("Выйти", on_click=lambda e: logout(page)),
                ], spacing=0),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                date_text,
                ft.IconButton(ft.Icons.CALENDAR_MONTH, tooltip="Календарь — зелёные дни с записями",
                              on_click=open_calendar),
                ft.IconButton(ft.Icons.PALETTE, tooltip="Тема оформления",
                              on_click=open_themes),
            ]),
            # Панель цели
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        goal_text,
                        ft.IconButton(ft.Icons.SETTINGS, icon_size=18, tooltip="Изменить цель",
                                      on_click=edit_goal),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    goal_bar,
                    goal_left,
                ]),
                bgcolor=ft.Colors.GREY_100,
                border_radius=10,
                padding=10,
            ),
            total,
            ft.Divider(),
            ft.Row([
                ft.Text("🍽 Продукты", size=16, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить продукт", on_click=add_food),
            ]),
            food_list,
            ft.Divider(),
            ft.Text("📝 Заметки", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([
                note_input,
                ft.IconButton(ft.Icons.MIC, tooltip="Надиктовать", on_click=voice_input),
                ft.IconButton(ft.Icons.SEND, tooltip="Сохранить", on_click=save_note),
            ], spacing=2),
            notes_list,
        ], scroll=ft.ScrollMode.AUTO, spacing=6)
    )

def logout(page):
    # полный выход: не запоминаем пользователя для автовхода
    from services.auth_store import clear_last_user
    clear_last_user()
    page.session.store.clear()
    from screens.login import login_screen
    login_screen(page)

def switch_user(page):
    # смена: остаёмся в памяти последним пользователем, но показываем форму входа
    page.session.store.clear()
    from screens.login import login_screen
    login_screen(page)
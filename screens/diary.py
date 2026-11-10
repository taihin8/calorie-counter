import flet as ft
from datetime import date, datetime, timedelta
from calendar import monthrange
import threading
import time
from database import (add_food_entry, get_daily_food, get_daily_calories,
                      add_note, get_notes, delete_note, update_note,
                      delete_food_entry, update_food_entry, get_entry_dates,
                      get_calorie_goal, set_calorie_goal, get_goal_progress,
                      get_theme, set_theme, get_note_font_size, set_note_font_size,
                      NOTE_FONT_SIZES)
from services.speech import recognize_async, parse_food_text
from services.themes import THEMES, apply_theme

GREEN = ft.Colors.GREEN_400
GREY = ft.Colors.GREY_300

def _shift_month(month_first, delta):
    """Первый день месяца ±delta месяцев (delta = -1 или +1)."""
    # −1: день назад от 1-го = 1-е прошлого месяца; +1: 1-е + 32 дня = 1-е следующего
    shifted = month_first - timedelta(days=1) if delta < 0 else month_first + timedelta(days=32)
    return shifted.replace(day=1)

def _log_error(context, ex):
    """Пишет ошибку в stdout и, если можно, в instance/crash.log.

    На Android каталог instance/ недоступен — раньше запись падала и причина
    терялась целиком, поэтому сначала всегда печатаем в stdout.
    """
    import os, sys, traceback
    text = f"[{context}] {ex}\n{traceback.format_exc()}"
    try:
        print(text, file=sys.stderr, flush=True)
    except Exception:
        pass
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'crash.log')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(text + "\n")
    except OSError:
        pass  # на Android писать некуда — уже вывели в stdout

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
    note_input = ft.TextField(label="Новая заметка", expand=True, multiline=True)
    notes_list = ft.Column(spacing=0)
    reminders_list = ft.Column(spacing=0)

    # скрытая кнопка-«приёмник» фокуса: перевод фокуса на неё снимает
    # клавиатуру (поле теряет фокус), а сама кнопка невидима (1×1, opacity=0)
    focus_sink = ft.IconButton(ft.Icons.CLOSE, opacity=0, width=1, height=1, padding=0,
                               on_click=lambda e: None)

    def dismiss_keyboard():
        page.run_task(focus_sink.focus)

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
        cal_month = datetime.strptime(selected_date, "%Y-%m-%d").replace(day=1)
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
            cal_month = _shift_month(cal_month, delta)
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

    # ---------- Будильники ----------
    def open_alarms(e):
        """Список будильников: тумблер, расписание, кнопка добавить."""
        from database import get_alarms, set_alarm_enabled, delete_alarm
        from services.alarm_service import format_schedule, SOUNDS

        container = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

        def render():
            container.controls.clear()
            alarms = get_alarms(user['id'])
            if not alarms:
                container.controls.append(ft.Text("Нет будильников", color=GREY))
            for a in alarms:
                def remove(ev, aid=a['id']):
                    delete_alarm(aid)
                    render()

                row_info = [ft.Text(format_schedule(a), size=14)]
                if a.get('last_fired'):
                    row_info.append(ft.Text(f"Последний звонок: {a['last_fired'][11:16]}",
                                            size=11, color=GREY))
                container.controls.append(
                    ft.Row([
                        ft.Switch(value=bool(a['enabled']),
                                  on_change=lambda ev, aid=a['id'], cur=a['enabled']:
                                      set_alarm_enabled(aid, 0 if cur else 1)),
                        ft.Column([
                            *row_info,
                            ft.Text(f"Звук: {SOUNDS[a['sound_id']]}", size=12, color=GREY),
                        ], expand=True, spacing=0),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18,
                                      tooltip="Удалить", on_click=remove),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                )
            page.update()

        def add(e):
            page.pop_dialog()
            from screens.alarm_editor import alarm_editor_dialog
            alarm_editor_dialog(page, user['id'], None, on_saved=render)

        dialog = ft.AlertDialog(
            title=ft.Text("Будильник"),
            content=container,
            actions=[
                ft.TextButton("Закрыть", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton("＋ Добавить", on_click=add),
            ],
        )
        page.show_dialog(dialog)
        render()
        alarms_refresh[0] = render

    # ---------- Обновления ----------
    def check_updates(e):
        from services.updater import check_for_update

        def do_check():
            info = check_for_update()
            # результат в поток Flet
            page.run_thread(lambda: show_result(info))

        def show_result(info):
            if info.get("error"):
                content = ft.Text(f"Не удалось проверить: {info['error']}")
                actions = [ft.TextButton("ОК", on_click=lambda e: page.pop_dialog())]
            elif info.get("has_update"):
                content = ft.Column([
                    ft.Text(f"Доступна новая версия {info['latest']}!"),
                    ft.Text("Скачаем APK внутри приложения и покажем, куда сохранили.",
                            size=12),
                    ft.Text("Если установка не запустится — скачайте через браузер.",
                            size=11, color=GREY),
                    ft.Text("Ссылка для скачивания:", size=11, color=GREY),
                    ft.Text(info.get("download_url") or "", size=11, selectable=True),
                ])
                actions = [
                    ft.TextButton("Позже", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton("Через браузер",
                                  on_click=lambda e: open_in_browser(info)),
                    ft.ElevatedButton("Скачать", on_click=lambda e: download_in_app(info)),
                ]
            else:
                from services.version import VERSION
                content = ft.Text(f"У вас последняя версия ({VERSION}).")
                actions = [ft.TextButton("ОК", on_click=lambda e: page.pop_dialog())]

            dialog = ft.AlertDialog(title=ft.Text("Обновление"), content=content,
                                    actions=actions)
            page.show_dialog(dialog)

        def open_downloaded(path):
            """Открывает скачанный APK. На Android нужен content:// через FileProvider
            (file:// запрещён с API 24). launch_url не ставит MIME/разрешение URI,
            поэтому открытие APK может не сработать — путь всегда виден в диалоге."""
            import os
            from pathlib import Path

            if page.platform != ft.PagePlatform.ANDROID:
                page.run_task(ft.UrlLauncher().launch_url, Path(path).as_uri())
                return
            # applicationId совпадает с AndroidManifest
            from services.version import ANDROID_APP_ID as pkg
            ext_root = "/storage/emulated/0"
            data_root = f"/data/data/{pkg}"
            if path.startswith(ext_root + "/"):
                prefix, root = "external_files", ext_root
            elif path.startswith(data_root + "/cache/"):
                prefix, root = "cache", data_root + "/cache"
            elif path.startswith(data_root + "/files/"):
                prefix, root = "files", data_root + "/files"
            else:
                page.show_dialog(ft.SnackBar(ft.Text("Файл сохранён:\n" + path)))
                return
            rel = path[len(root) + 1:].replace(os.sep, "/")
            page.run_task(ft.UrlLauncher().launch_url,
                          f"content://{pkg}.provider/{prefix}/{rel}")

        def open_in_browser(info):
            page.pop_dialog()
            url = info.get("download_url")
            if url:
                page.run_task(ft.UrlLauncher().launch_url, url)

        def download_in_app(info):
            page.pop_dialog()
            # launch_url — это async def; вызываем через run_task (иначе корутина теряется)
            page.run_task(run_download, info)

        async def run_download(info):
            import os
            from services.updater import download_apk

            url = info.get("download_url")
            if not url:
                from services.version import GITHUB_REPO
                await ft.UrlLauncher().launch_url(
                    f"https://github.com/{GITHUB_REPO}/releases")
                return

            # папка для сохранения: пробуем по очереди, последний вариант — домашняя
            paths = ft.StoragePaths()
            save_dir = None
            for getter in (paths.get_downloads_directory,
                           paths.get_application_documents_directory,
                           paths.get_external_storage_directory):
                try:
                    save_dir = await getter()
                except Exception:
                    save_dir = None
                if save_dir:
                    break
            if not save_dir:
                save_dir = os.path.expanduser("~")
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception:
                pass

            dest = os.path.join(save_dir, f"calorie-counter-{info['latest'].lstrip('v')}.apk")

            bar = ft.ProgressBar(value=0)
            status = ft.Text("Подготовка…", size=12)
            path_text = ft.Text("Сохраняем в: " + dest, size=11, selectable=True, color=GREY)
            hint = ft.Text("", size=11)
            open_btn = ft.TextButton(
                "Открыть файл", icon=ft.Icons.OPEN_IN_NEW,
                disabled=True,
                on_click=lambda e: open_downloaded(dest),
            )

            dialog = ft.AlertDialog(
                title=ft.Text("Скачивание обновления"),
                content=ft.Column([bar, status, path_text, hint, open_btn],
                                  spacing=6, tight=True),
                actions=[ft.TextButton("Закрыть", on_click=lambda e: page.pop_dialog())],
            )
            page.show_dialog(dialog)

            # троттлинг обновлений шкалы: не чаще раза в 300 мс
            last_tick = [0.0]

            def on_progress(done, total):
                now = time.time()
                if now - last_tick[0] < 0.3 and done < total:
                    return
                last_tick[0] = now
                bar.value = (done / total) if total else None
                status.value = (f"{done / 1048576:.1f} МБ из {total / 1048576:.1f} МБ"
                                if total else f"{done / 1048576:.1f} МБ")
                page.update()

            def worker():
                try:
                    download_apk(url, dest, on_progress)
                    bar.value = 1
                    status.value = "Готово"
                    open_btn.disabled = False
                    # Флет/Android не может сам показать инсталлятор с нужным MIME —
                    # подсказываем, что делать дальше.
                    hint.value = ("Если установка не открылась сама — нажмите «Открыть файл»\n"
                                  "и следуйте подсказкам системы.")
                    page.update()
                except Exception as ex:
                    status.value = f"Ошибка: {ex}"
                    page.update()

            page.run_thread(worker)

        page.run_thread(do_check)

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
        refresh_goal()
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
        find_btn = ft.TextButton("Найти калории", on_click=do_search,
                                 style=ft.ButtonStyle(visual_density=ft.VisualDensity.COMPACT))
        def save(dlg):
            if not name.value:
                status.value = "Введите название"
                status.color = ft.Colors.RED
                page.update()
                return
            if not cal_field.value:
                # не найден голосом — попробуем угадать по названию
                from services.food_db import guess_calories
                cal = guess_calories(name.value)
                if not cal:
                    status.value = "Укажите калории"
                    status.color = ft.Colors.RED
                    page.update()
                    return
                cal_field.value = str(cal).replace('.', ',')
            page.pop_dialog()
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
                name,
                ft.Row([find_btn, mic_btn], spacing=2),
                ft.Row([
                    ft.Container(cal_field, expand=True),
                    ft.Container(grams_field, expand=True),
                ], spacing=4),
                status,
            ], spacing=6, tight=True),
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
    note_font = [get_note_font_size(user['id'])]   # текущий размер шрифта

    def refresh_notes():
        notes = get_notes(user['id'])
        notes_list.controls.clear()
        size = note_font[0]
        for n in notes[:20]:
            # текст переносится целиком: раньше обрезался на 45 символах
            # и прочитать заметку можно было только открыв её на изменение
            notes_list.controls.append(
                ft.Row([
                    ft.Text(f"[{n['date']}] {n['text']}", size=size, expand=True,
                            no_wrap=False, selectable=True),
                    ft.Column([
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=14, width=26, height=26, padding=0,
                                      tooltip="Изменить",
                                      on_click=lambda _, nid=n['id'], txt=n['text']: edit_note(nid, txt)),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14, width=26, height=26, padding=0,
                                      tooltip="Удалить",
                                      on_click=lambda _, nid=n['id']: delete_and_refresh(nid)),
                    ], spacing=0),
                ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.START)
            )
        page.update()

    def set_font(size):
        """Меняет размер шрифта заметок и запоминает выбор."""
        note_font[0] = size
        try:
            set_note_font_size(user['id'], size)
        except Exception as ex:
            _log_error("note_font", ex)
        refresh_notes()

    def choose_font(e):
        chips = ft.Row(wrap=True, spacing=4, run_spacing=4)
        for size in NOTE_FONT_SIZES:
            chips.controls.append(
                ft.Chip(label=ft.Text(f"{size}"),
                        selected=(size == note_font[0]),
                        on_click=lambda ev, s=size: (set_font(s), page.pop_dialog()))
            )
        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Размер шрифта заметок"),
            content=chips,
            actions=[ft.TextButton("Закрыть", on_click=lambda e: page.pop_dialog())],
        ))

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

    # ---------- Напоминания о памятных днях ----------
    # ссылка на сервис уведомлений: заполняется при старте, нужна для перепланирования
    notifications_ref = [None]

    def refresh_notifications():
        """Пересоздаёт системные уведомления после правки напоминаний."""
        svc = notifications_ref[0]
        if svc is not None:
            try:
                svc.reschedule()
            except Exception as ex:
                _log_error("notifications", ex)

    def refresh_reminders():
        from database import get_reminders, delete_reminder
        from services.reminder_service import days_until, next_occurrence
        reminders_list.controls.clear()
        items = get_reminders(user['id'])
        if not items:
            reminders_list.controls.append(
                ft.Text("Нет напоминаний", size=12, color=GREY))
        today = date.today()
        for r in sorted(items, key=lambda x: days_until(x["remind_date"],
                                                        bool(x["annual"]), today)):
            days = days_until(r["remind_date"], bool(r["annual"]), today)
            if days == 0:
                when = "сегодня"
            elif days == 1:
                when = "завтра"
            else:
                when = f"через {days} дн."
            try:
                shown_date = next_occurrence(r["remind_date"], bool(r["annual"]), today)
                date_txt = shown_date.strftime("%d.%m.%Y")
            except Exception:
                date_txt = r["remind_date"]
            repeat = " · каждый год" if r["annual"] else ""

            def remove(ev, rid=r['id']):
                delete_reminder(rid)
                refresh_reminders()
                refresh_notifications()

            reminders_list.controls.append(
                ft.Row([
                    ft.Column([
                        ft.Text(r["text"], size=note_font[0], no_wrap=False),
                        ft.Text(f"{date_txt} · {when}{repeat}", size=10, color=GREY),
                    ], expand=True, spacing=0),
                    ft.Column([
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=14, width=26,
                                      height=26, padding=0, tooltip="Изменить",
                                      on_click=lambda _, rid=r['id']: reminder_dialog(rid)),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14, width=26,
                                      height=26, padding=0, tooltip="Удалить",
                                      on_click=remove),
                    ], spacing=0),
                ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.START)
            )
        page.update()

    def reminder_dialog(reminder_id=None):
        """Добавление (id=None) или правка напоминания."""
        from database import get_reminder, add_reminder, update_reminder, delete_reminder
        from services.reminder_service import validate_reminder

        existing = get_reminder(reminder_id) if reminder_id else None
        date_field = ft.TextField(
            label="Дата (ГГГГ-ММ-ДД)",
            value=existing["remind_date"] if existing else date.today().isoformat(),
            keyboard_type=ft.KeyboardType.DATETIME)
        text_field = ft.TextField(
            label="Описание", value=existing["text"] if existing else "",
            autofocus=reminder_id is None)
        annual_sw = ft.Switch(label="Каждый год",
                              value=bool(existing["annual"]) if existing else True)
        error = ft.Text("", size=11, color=ft.Colors.RED)

        def pick_date(e):
            """Календарь для выбора даты — не надо набирать вручную."""
            def on_change(ev):
                if picker.value:
                    date_field.value = picker.value.strftime("%Y-%m-%d")
                page.pop_dialog()
                page.update()

            picker = ft.DatePicker(
                value=date_field.value,
                first_date=date(1900, 1, 1),
                last_date=date(2100, 12, 31),
                on_change=on_change,
            )
            page.show_dialog(picker)

        def save(e):
            try:
                validate_reminder(date_field.value, text_field.value)
            except ValueError as ex:
                error.value = str(ex)
                page.update()
                return
            page.pop_dialog()
            if reminder_id:
                update_reminder(reminder_id, date_field.value, text_field.value.strip(),
                                int(annual_sw.value))
            else:
                add_reminder(user['id'], date_field.value, text_field.value.strip(),
                             int(annual_sw.value))
            refresh_reminders()
            refresh_notifications()

        def remove(e):
            page.pop_dialog()
            if reminder_id:
                delete_reminder(reminder_id)
            refresh_reminders()

        actions = [ft.TextButton("Отмена", on_click=lambda e: page.pop_dialog())]
        if reminder_id:
            actions.append(ft.TextButton("Удалить", on_click=remove))
        actions.append(ft.ElevatedButton("Сохранить", on_click=save))

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Напоминание" if not reminder_id else "Изменить напоминание"),
            content=ft.Column([
                ft.Row([date_field,
                        ft.IconButton(ft.Icons.CALENDAR_MONTH, tooltip="Выбрать дату",
                                      on_click=pick_date)], spacing=2),
                text_field,
                annual_sw,
                ft.Text("Окно появится за день до даты и в саму дату.", size=10,
                        color=GREY),
                error,
            ], spacing=6, tight=True),
            actions=actions,
        ))

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
    refresh_reminders()

    # ---------- Будильник: фоновый опрос расписания ----------
    def _ring(alarm, point):
        """Вызывается из потока планировщика — звонок показываем в UI-потоке."""
        def show():
            try:
                from screens.alarm_ring import show_ring
                show_ring(page, alarm, point)
                refresh_alarms_if_open()
            except Exception as ex:
                _log_error("alarm_ring", ex)
                # на Android stderr не виден, поэтому причину показываем в UI
                try:
                    page.show_dialog(ft.AlertDialog(
                        title=ft.Text("Ошибка будильника"),
                        content=ft.Text(f"{type(ex).__name__}: {ex}"),
                        actions=[ft.TextButton("ОК", on_click=lambda e: page.pop_dialog())],
                    ))
                except Exception:
                    pass
        page.run_thread(show)

    def refresh_alarms_if_open():
        """Обновляет открытый список будильников, если он показан."""
        try:
            if alarms_refresh[0]:
                alarms_refresh[0]()
        except Exception:
            pass

    alarms_refresh = [None]
    from services.alarm_runner import AlarmRunner
    _runner = AlarmRunner(user['id'], _ring)
    _runner.start()

    # ---------- Напоминания: проверка дат ----------
    def _remind(reminder, stage):
        """Вызывается из потока планировщика — окно показываем в UI-потоке."""
        def show():
            try:
                from services.reminder_service import reminder_text
                text = reminder_text(reminder, stage)
                title = "🎂 Напоминание" if stage == "day" else "🎂 Скоро"
                page.show_dialog(ft.AlertDialog(
                    modal=True,
                    title=ft.Text(title),
                    content=ft.Text(text, size=15),
                    actions=[ft.ElevatedButton("Понятно",
                                               on_click=lambda e: page.pop_dialog())],
                ))
                refresh_reminders()
            except Exception as ex:
                _log_error("reminder", ex)
        page.run_thread(show)

    from services.reminder_runner import ReminderRunner
    _reminder_runner = ReminderRunner(user['id'], _remind)
    _reminder_runner.start()

    # нативные уведомления: нужны, чтобы напоминание пришло при закрытом приложении
    from services.notifications import ReminderNotifications
    _notifications = ReminderNotifications(page, user['id'])
    notifications_ref[0] = _notifications
    page.run_thread(_notifications.start)

    # автообновление каждые 10 сек — чтобы подтягивать данные с телефона
    def _auto_refresh():
        while True:
            time.sleep(10)
            try:
                page.run_thread(lambda: (refresh(), refresh_notes()))
            except Exception:
                break
    t = threading.Thread(target=_auto_refresh, daemon=True)
    t.start()

    page.add(
        ft.GestureDetector(
            expand=True,
            on_tap_down=lambda e: dismiss_keyboard(),
            content=ft.SafeArea(
                expand=True,
                content=ft.Column([
                focus_sink,
                ft.Row([
                    ft.Text(f"👤 {user['username']}", size=14, color=ft.Colors.GREY),
                    ft.Row([
                        ft.IconButton(ft.Icons.SYSTEM_UPDATE, icon_size=18, width=32, height=32, padding=0,
                                      tooltip="Проверить обновления",
                                      on_click=check_updates),
                        ft.TextButton("Сменить", tooltip="Сменить пользователя",
                                      on_click=lambda e: switch_user(page)),
                        ft.TextButton("Выйти", on_click=lambda e: logout(page)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    date_text,
                    ft.IconButton(ft.Icons.CALENDAR_MONTH, tooltip="Календарь — зелёные дни с записями",
                                  on_click=open_calendar),
                    ft.IconButton(ft.Icons.NOTIFICATIONS_ACTIVE, tooltip="Будильник",
                                  on_click=open_alarms),
                    ft.IconButton(ft.Icons.PALETTE, tooltip="Тема оформления",
                                  on_click=open_themes),
                ]),
                # Вкладки: калькулятор калорий и заметки
                ft.Tabs(
                    length=3,
                    expand=True,
                    content=ft.Column([
                        ft.TabBar(tabs=[
                            ft.Tab(label="Калькулятор", icon=ft.Icons.RESTAURANT_MENU),
                            ft.Tab(label="Заметки", icon=ft.Icons.EDIT_NOTE),
                            ft.Tab(label="Напоминания", icon=ft.Icons.CAKE),
                        ]),
                        ft.TabBarView(expand=True, controls=[
                            # --- вкладка 1: цель и продукты ---
                            ft.Column([
                                ft.Container(
                                    content=ft.Column([
                                        ft.Row([
                                            goal_text,
                                            ft.IconButton(ft.Icons.SETTINGS, icon_size=18,
                                                          tooltip="Изменить цель",
                                                          on_click=edit_goal),
                                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                        goal_bar,
                                        goal_left,
                                    ]),
                                    bgcolor=ft.Colors.GREY_100,
                                    border_radius=10,
                                    padding=10,
                                ),
                                ft.Row([
                                    total,
                                    ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить продукт",
                                                  on_click=add_food),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                food_list,
                            ], spacing=6, scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                            # --- вкладка 2: заметки ---
                            ft.Column([
                                ft.Row([
                                    note_input,
                                    ft.IconButton(ft.Icons.MIC, tooltip="Надиктовать",
                                                  on_click=voice_input),
                                    ft.IconButton(ft.Icons.SEND, tooltip="Сохранить",
                                                  on_click=save_note),
                                ], spacing=2),
                                ft.Row([
                                    ft.Text("📝 Заметки", size=14,
                                            weight=ft.FontWeight.BOLD, expand=True),
                                    ft.IconButton(ft.Icons.FORMAT_SIZE,
                                                  tooltip="Размер шрифта заметок",
                                                  icon_size=18, on_click=choose_font),
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                notes_list,
                            ], spacing=6, scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                            # --- вкладка 3: напоминания ---
                            ft.Column([
                                ft.Row([
                                    ft.Text("🎂 Памятные дни", size=14,
                                            weight=ft.FontWeight.BOLD, expand=True),
                                    ft.IconButton(ft.Icons.ADD_CIRCLE,
                                                  tooltip="Добавить напоминание",
                                                  on_click=lambda e: reminder_dialog()),
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                ft.Text("Всплывающее окно появится за день до даты "
                                        "и в саму дату.", size=10, color=GREY),
                                reminders_list,
                            ], spacing=6, scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                        ]),
                    ], expand=True, spacing=0),
                ),
            ], expand=True, spacing=6),
            )
        )
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
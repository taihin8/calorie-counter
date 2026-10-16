import flet as ft
from datetime import date
from database import add_food_entry, get_daily_food, get_daily_calories, add_note, get_notes, delete_note

def diary_screen(page: ft.Page):
    user = page.session.get("user")
    if not user:
        from screens.login import login_screen
        login_screen(page)
        return

    page.clean()
    selected_date = str(date.today())
    total = ft.Text("0 ккал", size=22, weight=ft.FontWeight.BOLD)
    food_list = ft.Column()
    note_input = ft.TextField(label="Новая заметка", width=300, multiline=True)
    notes_list = ft.Column()

    def refresh():
        nonlocal total
        entries = get_daily_food(user['id'], selected_date)
        food_list.controls.clear()
        for e in entries:
            food_list.controls.append(
                ft.Text(f"{e['product_name']} — {e['calories']:.0f} ккал ({e['grams']:.0f} г)", size=14)
            )
        cal = get_daily_calories(user['id'], selected_date)
        total.value = f"{cal:.0f} ккал"
        page.update()

    def add_food(e):
        dialog = ft.AlertDialog(
            title=ft.Text("Добавить продукт"),
            content=ft.Column([
                ft.TextField(label="Название", autofocus=True),
                ft.TextField(label="Калорий на 100г", keyboard_type=ft.KeyboardType.NUMBER),
                ft.TextField(label="Грамм", value="100", keyboard_type=ft.KeyboardType.NUMBER),
            ]),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.close(dialog)),
                ft.ElevatedButton("Добавить", on_click=lambda e: save_food(dialog)),
            ]
        )
        page.open(dialog)

    def save_food(dialog):
        fields = dialog.content.controls
        name = fields[0].value
        cal_str = fields[1].value
        grams_str = fields[2].value
        page.close(dialog)
        if name and cal_str:
            add_food_entry(user['id'], name, float(cal_str), float(grams_str or 100), selected_date)
            refresh()

    def save_note(e):
        if note_input.value:
            add_note(user['id'], note_input.value, selected_date)
            note_input.value = ""
            refresh_notes()

    def refresh_notes():
        notes = get_notes(user['id'])
        notes_list.controls.clear()
        for n in notes[:10]:
            notes_list.controls.append(
                ft.Row([
                    ft.Text(f"[{n['date']}] {n['text'][:50]}...", size=12, expand=True),
                    ft.IconButton(ft.Icons.DELETE, icon_size=16, on_click=lambda _, nid=n['id']: delete_and_refresh(nid)),
                ])
            )
        page.update()

    def delete_and_refresh(nid):
        delete_note(nid)
        refresh_notes()

    refresh()
    refresh_notes()

    page.add(
        ft.Column([
            ft.Row([
                ft.Text(f"👤 {user['username']}", size=14, color=ft.Colors.GREY),
                ft.TextButton("Выйти", on_click=lambda e: logout(page)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text(selected_date, size=16),
            total,
            ft.Divider(),
            ft.Row([
                ft.Text("🍽 Продукты", size=16, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=add_food),
            ]),
            food_list,
            ft.Divider(),
            ft.Text("📝 Заметки", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([note_input, ft.IconButton(ft.Icons.SEND, on_click=save_note)]),
            notes_list,
        ], scroll=ft.ScrollMode.AUTO)
    )

def logout(page):
    page.session.clear()
    from screens.login import login_screen
    login_screen(page)

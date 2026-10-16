import flet as ft
from services.auth_store import get_last_user, save_last_user

def login_screen(page: ft.Page):
    page.clean()
    page.title = "Calorie Counter"
    page.window.width = 480
    page.window.height = 800

    last = get_last_user() or ""
    username = ft.TextField(label="Логин", width=340, value=last, autofocus=not last)
    password = ft.TextField(label="Пароль", width=340, password=True, autofocus=bool(last))
    error = ft.Text("", color=ft.Colors.RED)

    def do_login(e):
        from database import get_user
        user = get_user(username.value, password.value)
        if user:
            save_last_user(username.value)
            page.session.store.set("user", user)
            from screens.diary import diary_screen
            diary_screen(page)
        else:
            error.value = "Неверный логин или пароль"
            page.update()

    def do_register(e):
        from database import add_user
        result = add_user(username.value, password.value)
        if result:
            error.value = "Пользователь создан! Войдите."
            error.color = ft.Colors.GREEN
        else:
            error.value = "Пользователь уже существует"
            error.color = ft.Colors.RED
        page.update()

    # Enter в любом поле = вход
    username.on_submit = do_login
    password.on_submit = do_login

    page.add(
        ft.Column([
            ft.Text("🥗 Calorie Counter", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Дневник питания", size=14, color=ft.Colors.GREY),
            ft.Divider(height=30),
            username,
            password,
            ft.Row([
                ft.ElevatedButton("Войти", on_click=do_login),
                ft.TextButton("Регистрация", on_click=do_register),
            ], alignment=ft.MainAxisAlignment.CENTER),
            error,
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

import flet as ft

def login_screen(page: ft.Page):
    page.clean()
    page.title = "Calorie Counter"
    page.window.width = 400
    page.window.height = 700

    username = ft.TextField(label="Логин", width=300, autofocus=True)
    password = ft.TextField(label="Пароль", width=300, password=True)
    error = ft.Text("", color=ft.Colors.RED)

    def do_login(e):
        from database import get_user
        user = get_user(username.value, password.value)
        if user:
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

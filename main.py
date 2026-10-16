import flet as ft
from database import init_db, get_user_by_username
from services.auth_store import get_last_user

def main(page: ft.Page):
    init_db()
    # автовход: открываем дневник последнего пользователя сразу
    last = get_last_user()
    if last:
        user = get_user_by_username(last)
        if user:
            page.session.store.set("user", user)
            from screens.diary import diary_screen
            diary_screen(page)
            return
    from screens.login import login_screen
    login_screen(page)

if __name__ == "__main__":
    ft.app(target=main)
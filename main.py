import flet as ft
from database import init_db
from screens.login import login_screen

def main(page: ft.Page):
    init_db()
    login_screen(page)

if __name__ == "__main__":
    ft.app(target=main)
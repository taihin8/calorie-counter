import sys
import ctypes
import flet as ft
from database import init_db, get_user_by_username
from services.auth_store import get_last_user

# Одно окно: если приложение уже запущено — новый процесс сразу выходит
# (не открываем второе окно поверх старого)
MUTEX_NAME = "CalorieCounter_DSH_SingleInstance"

def _ensure_single_instance():
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    already_running = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    if already_running:
        sys.exit(0)

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
    _ensure_single_instance()
    ft.app(target=main)
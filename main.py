import sys
import ctypes
import subprocess
import os
import flet as ft
from database import init_db, get_user_by_username
from services.auth_store import get_last_user

# Одно окно: если приложение уже запущено — новый процесс сразу выходит.
# Web-режим (CALORIE_MODE=web) не блокирует, чтобы десктоп + web
# могли работать одновременно с одной БД.
MUTEX_NAME = "CalorieCounter_DSH_SingleInstance"
_MUTEX_HANDLE = None  # держим дескриптор живым до конца процесса


def _ensure_single_instance():
    if os.environ.get("CALORIE_MODE") == "web":
        return  # web-режим не блокирует
    global _MUTEX_HANDLE
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    already_running = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
    if already_running:
        sys.exit(0)


def _cleanup_orphan_windows():
    """Убирает осиротевшие окна flet (остались после убитого pythonw) —
    те самые «Warning». Убиваем только клиенты НАШЕГО приложения."""
    try:
        assets = os.path.dirname(os.path.abspath(__file__)).replace("\\", "\\\\")
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='flet.exe'\" | "
            f"Where-Object {{ $_.CommandLine -like '*{assets}*' }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=15)
    except Exception:
        pass


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
    _cleanup_orphan_windows()
    ft.app(target=main)
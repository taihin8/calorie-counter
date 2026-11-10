"""Нативные уведомления: модуль не должен ломать приложение без пакета."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.notifications import ReminderNotifications


class _Page:
    """Заглушка страницы: сервис недоступен, вызовы в поток не уходят."""
    def run_task(self, *a, **k):
        raise AssertionError("без пакета задачи запускаться не должны")

    def run_thread(self, *a, **k):
        raise AssertionError("без пакета потоки запускаться не должны")


def test_start_without_package_returns_false(monkeypatch):
    """Если пакета нет (десктоп, старая сборка), старт тихо выключается."""
    monkeypatch.setitem(sys.modules, "flet_android_notifications", None)
    svc = ReminderNotifications(_Page(), 1)
    assert svc.start() is False
    assert svc.enabled is False


def test_reschedule_without_service_is_noop():
    """Без включённого сервиса перепланирование ничего не делает и не падает."""
    svc = ReminderNotifications(_Page(), 1)
    svc.reschedule()          # enabled=False — должен просто выйти
    assert svc.enabled is False

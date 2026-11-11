"""Сервис будильника: включается только при включённых будильниках.

При сворачивании Android морозит приложение, и поток планировщика встаёт —
будильник не звонит. Foreground-сервис держит процесс живым.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.notifications import NativeNotifications, service_needed


class _Page:
    """Страница-заглушка: без пакета задачи и потоки не должны запускаться."""
    def run_task(self, *a, **k):
        raise AssertionError("без пакета задачи запускаться не должны")

    def run_thread(self, *a, **k):
        raise AssertionError("без пакета потоки запускаться не должны")


def test_service_needed_only_for_enabled():
    """Сервис нужен, только когда есть включённый будильник."""
    assert service_needed([]) is False
    assert service_needed([{"enabled": 0}]) is False
    assert service_needed([{"enabled": 1}]) is True


def test_service_needed_treats_missing_flag_as_enabled():
    """Нет флага enabled — считаем включённым (как в due_point)."""
    assert service_needed([{}]) is True
    assert service_needed([{"enabled": 0}, {}]) is True


def test_start_without_package_returns_false(monkeypatch):
    """Если пакета нет (десктоп, старая сборка), старт тихо выключается."""
    monkeypatch.setitem(sys.modules, "flet_android_notifications", None)
    svc = NativeNotifications(_Page(), 1)
    assert svc.start() is False
    assert svc.enabled is False


def test_refresh_without_service_is_noop():
    """Без включённого сервиса обновление ничего не делает и не падает."""
    svc = NativeNotifications(_Page(), 1)
    svc.refresh()
    assert svc.enabled is False
    assert svc.service_running is False


def test_service_running_flag_defaults_false():
    """До старта сервис считается выключенным."""
    svc = NativeNotifications(_Page(), 1)
    assert svc.service_running is False

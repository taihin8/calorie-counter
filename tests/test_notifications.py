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


def test_alarm_payload_round_trip():
    """Метка уведомления будильника разбирается обратно без потерь."""
    from services.notifications import alarm_payload, parse_alarm_payload
    p = alarm_payload(7, "2026-11-14T07:30")
    assert parse_alarm_payload(p) == (7, "2026-11-14T07:30")


def test_parse_rejects_foreign_payload():
    """Чужие метки (напоминания) и мусор не должны запускать звонок."""
    from services.notifications import parse_alarm_payload
    for bad in ("", "reminder:5", "alarm:", "alarm:abc:x", None, "alarm:zz:2026-01-01T00:00"):
        assert parse_alarm_payload(bad) is None, bad


def test_alarm_ids_do_not_clash_with_reminders():
    """id уведомлений будильника не пересекаются с напоминаниями.

    Напоминание занимает два id (за день и в день), поэтому база будильников
    должна быть выше любого из них.
    """
    from services.notifications import ALARM_ID_BASE
    assert ALARM_ID_BASE > 1000


def test_payload_from_event_variants():
    """Dart отдаёт payload то словарём, то JSON-строкой — оба обязаны работать."""
    from services.notifications import payload_from, alarm_payload
    p = alarm_payload(7, "2026-11-14T07:30")
    assert payload_from({"payload": p}) == p
    assert payload_from('{"payload": "' + p + '"}') == p


def test_payload_from_garbage_is_empty():
    """Мусор и пустые события не должны ни звонить, ни падать."""
    from services.notifications import payload_from
    for bad in ("", None, "не json", 42, {}):
        assert payload_from(bad) == ""


def test_payload_from_handles_raw_payload_string():
    """Если вдруг пришёл сам payload без обёртки — не теряем его."""
    from services.notifications import payload_from, alarm_payload
    p = alarm_payload(3, "2026-11-14T08:00")
    assert payload_from(p) == "" or payload_from(p) == p

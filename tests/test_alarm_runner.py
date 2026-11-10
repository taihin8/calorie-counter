import sys, os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.alarm_runner import due_point, should_fire, find_due, GRACE


def _alarm(**kw):
    a = dict(id=1, enabled=1, days="1111111", start_time="09:00",
             end_time="09:00", interval_minutes=60, sound_id=0, last_fired=None)
    a.update(kw)
    return a


def test_due_point_inside_grace():
    """Точка 09:00 при опросе в 09:00:30 — пора звонить."""
    now = datetime(2026, 11, 9, 9, 0, 30)
    assert due_point(_alarm(), now) == datetime(2026, 11, 9, 9, 0)


def test_due_point_too_old_is_skipped():
    """Точка старше окна не навёрстывается (приложение было закрыто)."""
    now = datetime(2026, 11, 9, 11, 0)
    assert due_point(_alarm(), now) is None


def test_due_point_wrong_day_and_disabled():
    alarm = _alarm(days="0000011")          # только сб/вс
    assert due_point(alarm, datetime(2026, 11, 9, 9, 0)) is None   # понедельник
    assert due_point(_alarm(enabled=0), datetime(2026, 11, 9, 9, 0)) is None


def test_should_fire_respects_last_fired():
    point = datetime(2026, 11, 9, 9, 0)
    assert should_fire(_alarm(), point) is True
    assert should_fire(_alarm(last_fired=point.isoformat()), point) is False
    earlier = (point - timedelta(minutes=60)).isoformat()
    assert should_fire(_alarm(last_fired=earlier), point) is True


def test_find_due_returns_first_due_alarm():
    now = datetime(2026, 11, 9, 9, 0, 10)
    alarms = [_alarm(id=1, start_time="08:00", end_time="08:00"),
              _alarm(id=2, start_time="09:00", end_time="09:00")]
    found = find_due(alarms, now)
    assert found is not None
    alarm, point = found
    assert alarm["id"] == 2 and point == datetime(2026, 11, 9, 9, 0)


def test_find_due_none_when_nothing_due():
    now = datetime(2026, 11, 9, 12, 30)
    assert find_due([_alarm()], now) is None


def test_grace_is_short_window():
    assert GRACE <= timedelta(minutes=5)

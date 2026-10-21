import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from datetime import date, datetime
from services.alarm_service import (
    parse_time, validate_alarm, alarm_points, schedule_for_day,
    format_schedule, next_occurrence, DAY_PRESETS,
)

def test_parse_time():
    assert parse_time("00:00") == 0
    assert parse_time("23:59") == 23 * 60 + 59
    with pytest.raises(ValueError):
        parse_time("24:00")
    with pytest.raises(ValueError):
        parse_time("12:60")

def test_validate_ok():
    validate_alarm("11:00", "20:00", 60, "1111100", 0)

def test_validate_end_before_start():
    with pytest.raises(ValueError):
        validate_alarm("20:00", "11:00", 60, "1111111", 0)
    with pytest.raises(ValueError):
        validate_alarm("11:00", "11:00", 60, "1111111", 0)

def test_validate_interval():
    with pytest.raises(ValueError):
        validate_alarm("08:00", "09:00", 45, "1111111", 0)

def test_validate_days():
    with pytest.raises(ValueError):
        validate_alarm("08:00", "09:00", 60, "0000000", 0)
    with pytest.raises(ValueError):
        validate_alarm("08:00", "09:00", 60, "11111", 0)

def test_validate_sound():
    with pytest.raises(ValueError):
        validate_alarm("08:00", "09:00", 60, "1111111", 99)

def test_points_example_from_spec():
    # Спецификация: 11:00–20:00, шаг 60 → 10 звонков включая 20:00
    pts = alarm_points("11:00", "20:00", 60, "1111111")
    assert len(pts) == 10
    assert pts[0] == 11 * 60
    assert pts[-1] == 20 * 60

def test_points_endpoint_included():
    # endTime включается, следующая точка за окном — нет
    pts = alarm_points("11:00", "20:30", 60, "1111111")
    assert pts[-1] == 20 * 60

def test_schedule_skips_marked_days():
    alarm = {"enabled": 1, "days": "1111100",  # Пн–Пт
             "start_time": "09:00", "end_time": "10:00", "interval_minutes": 60}
    # 2026-10-21 — среда (рабочий), 2026-10-25 — воскресенье
    assert len(schedule_for_day(alarm, date(2026, 10, 21))) == 2
    assert schedule_for_day(alarm, date(2026, 10, 25)) == []

def test_schedule_disabled_returns_empty():
    alarm = {"enabled": 0, "days": "1111111",
             "start_time": "09:00", "end_time": "10:00", "interval_minutes": 60}
    assert schedule_for_day(alarm, date(2026, 10, 21)) == []

def test_format_schedule_presets():
    a = {"days": DAY_PRESETS["weekdays"], "start_time": "11:00",
         "end_time": "20:00", "interval_minutes": 60}
    assert format_schedule(a) == "Будни · 11:00–20:00 · каждый час"
    a["days"] = DAY_PRESETS["every_day"]
    assert format_schedule(a).startswith("Каждый день")

def test_next_occurrence_is_future():
    alarm = {"enabled": 1, "days": "1111111",
             "start_time": "09:00", "end_time": "10:00", "interval_minutes": 60}
    now = datetime(2026, 10, 21, 8, 0)
    assert next_occurrence(alarm, now) == datetime(2026, 10, 21, 9, 0)
    # уже после всех точек — переносится на завтра
    now = datetime(2026, 10, 21, 10, 30)
    assert next_occurrence(alarm, now) == datetime(2026, 10, 22, 9, 0)
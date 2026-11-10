"""Логика напоминаний: ежегодные даты, стадии «за день» и «в день»."""
import sys, os
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.reminder_service import (
    parse_date, validate_reminder, next_occurrence, days_until, due_stage,
    due_reminders, reminder_text,
)
from services.reminder_runner import pending


def _r(date_str, text="День рождения", annual=1, last_stage=None):
    return {"id": 1, "remind_date": date_str, "text": text,
            "annual": annual, "last_stage": last_stage}


def test_parse_date_and_validation():
    assert parse_date("2026-11-10") == date(2026, 11, 10)
    for bad in ("10.11.2026", "2026-13-01", "", None):
        try:
            parse_date(bad); assert False, f"принято {bad!r}"
        except ValueError:
            pass
    validate_reminder("2026-11-10", "День рождения")
    try:
        validate_reminder("2026-11-10", "   "); assert False, "пустое описание принято"
    except ValueError:
        pass


def test_annual_rolls_to_next_year():
    """Прошедшая дата в этом году переносится на следующий."""
    today = date(2026, 11, 10)
    assert next_occurrence("2020-03-05", True, today) == date(2027, 3, 5)
    assert next_occurrence("2020-12-31", True, today) == date(2026, 12, 31)


def test_non_annual_keeps_exact_date():
    """Без ежегодности дата фиксированная, даже если уже прошла."""
    today = date(2026, 11, 10)
    assert next_occurrence("2020-03-05", False, today) == date(2020, 3, 5)
    assert days_until("2020-03-05", False, today) < 0


def test_feb_29_falls_back_in_common_year():
    """29 февраля в невисокосный год — 28 февраля, без падения."""
    assert next_occurrence("2000-02-29", True, date(2026, 11, 10)) == date(2027, 2, 28)


def test_stages_lead_and_day():
    today = date(2026, 11, 10)
    assert due_stage("2000-11-11", True, today) == "lead"    # завтра
    assert due_stage("2000-11-10", True, today) == "day"     # сегодня
    assert due_stage("2000-11-20", True, today) is None      # далеко


def test_due_reminders_returns_both_stages():
    today = date(2026, 11, 10)
    got = due_reminders([_r("2000-11-11"), _r("2000-11-10"), _r("2000-12-01")], today)
    stages = sorted(s for _, s in got)
    assert stages == ["day", "lead"]


def test_pending_skips_already_shown_stage():
    """Повторно то же окно в тот же день не показываем."""
    today = date(2026, 11, 10)
    already = _r("2000-11-10", last_stage=f"day:{today.isoformat()}")
    assert pending([already], today) == []
    # а вчерашняя отметка не мешает сегодняшнему показу
    yesterday = _r("2000-11-10", last_stage="day:2026-11-09")
    assert len(pending([yesterday], today)) == 1


def test_lead_mark_does_not_block_day():
    """Отметка «за день» не должна заглушить показ в саму дату."""
    today = date(2026, 11, 11)
    r = _r("2000-11-11", last_stage="lead:2026-11-10")
    assert len(pending([r], today)) == 1


def test_reminder_text_mentions_when():
    today = date(2026, 11, 10)
    assert "сегодня" in reminder_text(_r("2000-11-10"), "day", today)
    assert "завтра" in reminder_text(_r("2000-11-11"), "lead", today)

def test_next_fire_time_moves_past_to_next_year():
    """Прошедшее сегодня время не теряется: переносится на следующий год.

    Раньше такое уведомление не планировалось вовсе — система не показывает
    уведомление в прошлом, а следующего года никто не ставил.
    """
    from datetime import datetime
    from services.reminder_service import next_fire_time

    now = datetime(2026, 11, 10, 12, 0)      # полдень: 9:00 уже прошло
    got = next_fire_time("2000-11-10", True, 0, now=now)
    assert got == datetime(2027, 11, 10, 9, 0)

    # если время ещё не наступило — планируем сегодня
    now = datetime(2026, 11, 10, 7, 0)
    assert next_fire_time("2000-11-10", True, 0, now=now) == datetime(2026, 11, 10, 9, 0)


def test_next_fire_time_returns_none_for_past_one_off():
    """Разовое напоминание в прошлом планировать некуда."""
    from datetime import datetime
    from services.reminder_service import next_fire_time
    now = datetime(2026, 11, 10, 12, 0)
    assert next_fire_time("2020-03-05", False, 0, now=now) is None
    assert next_fire_time("2026-11-10", False, 0, now=now) is None

"""Напоминания о памятных днях: расчёт ближайших срабатываний.

День рождения или другая памятная дата повторяется каждый год, поэтому у
напоминания есть флаг `annual`. Срабатываем дважды: за день до даты и в саму
дату — чтобы было время подготовиться.
"""
from datetime import date, datetime, timedelta

# за сколько дней предупреждаем заранее (за день до даты)
LEAD_DAYS = 1


def parse_date(value: str) -> date:
    """'ГГГГ-ММ-ДД' -> date. Бросает ValueError с понятным текстом."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("Дата должна быть в виде ГГГГ-ММ-ДД")


def validate_reminder(remind_date: str, text: str) -> None:
    """Проверяет поля напоминания; бросает ValueError с русским текстом."""
    parse_date(remind_date)
    if not (text or "").strip():
        raise ValueError("Введите описание напоминания")


def _this_year(remind: date, year: int) -> date:
    """Дата в указанном году; 29 февраля в невисокосный год -> 28 февраля."""
    try:
        return remind.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def occurrence_in_year(remind: date, annual: bool, year: int) -> date:
    """Когда напоминание случается в этом году."""
    return _this_year(remind, year) if annual else remind


def next_occurrence(remind_date, annual: bool, today: date = None) -> date:
    """Ближайшая дата напоминания (сегодня или позже)."""
    today = today or date.today()
    remind = parse_date(remind_date) if isinstance(remind_date, str) else remind_date
    if not annual:
        return remind
    for year in (today.year, today.year + 1):
        candidate = occurrence_in_year(remind, True, year)
        if candidate >= today:
            return candidate
    return occurrence_in_year(remind, True, today.year + 1)


def days_until(remind_date, annual: bool, today: date = None) -> int:
    """Сколько дней до ближайшего напоминания (0 = сегодня)."""
    today = today or date.today()
    return (next_occurrence(remind_date, annual, today) - today).days


def due_stage(remind_date, annual: bool, today: date = None):
    """Стадия срабатывания: 'day' — сегодня, 'lead' — за день, иначе None."""
    today = today or date.today()
    delta = days_until(remind_date, annual, today)
    if delta == 0:
        return "day"
    if delta == LEAD_DAYS:
        return "lead"
    return None


def due_reminders(reminders, today: date = None):
    """Список (напоминание, стадия) для тех, кому пора показать окно."""
    today = today or date.today()
    out = []
    for r in reminders:
        stage = due_stage(r["remind_date"], bool(r.get("annual", 1)), today)
        if stage:
            out.append((r, stage))
    return out


def reminder_text(reminder: dict, stage: str, today: date = None) -> str:
    """Текст всплывающего окна для стадии."""
    today = today or date.today()
    days = days_until(reminder["remind_date"], bool(reminder.get("annual", 1)), today)
    when = "сегодня" if stage == "day" else "завтра"
    years = ""
    if reminder.get("annual"):
        try:
            born = parse_date(reminder["remind_date"])
            age = today.year - born.year
            if age > 0:
                years = f" · {age} год" if age % 10 == 1 and age % 100 != 11 else f" · {age} лет"
        except ValueError:
            pass
    return f"{reminder['text']} — {when}{years}"


def sort_key(reminder: dict, today: date = None):
    """Порядок в списке: ближайшие сверху."""
    return days_until(reminder["remind_date"], bool(reminder.get("annual", 1)), today)

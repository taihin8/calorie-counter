"""Будильник: валидация настроек и расчёт точек срабатывания."""
from datetime import datetime, timedelta

# Шаги интервала, разрешённые спецификацией (15/30/60/120 мин)
ALLOWED_INTERVALS = (15, 30, 60, 120)
# Имена встроенных звуков (id = индекс в списке)
SOUNDS = ["Дождь", "Ручей", "Лес", "Озеро", "Ветер"]
# Пресеты дней недели: '0'=Пн … '6'=Вс (monday=0)
DAY_PRESETS = {
    "every_day": "1111111",
    "weekdays":  "1111100",
    "weekends":  "0000011",
}
DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def parse_time(value: str) -> int:
    """'HH:mm' -> минуты с полуночи. Бросает ValueError при мусоре."""
    h, m = value.split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Неверное время: {value}")
    return h * 60 + m


def validate_alarm(start_time: str, end_time: str, interval_minutes: int,
                   days: str, sound_id: int) -> None:
    """Проверяет настройки; бросает ValueError с русским текстом."""
    start = parse_time(start_time)
    end = parse_time(end_time)
    if end <= start:
        raise ValueError("Окончание должно быть позже начала")
    if interval_minutes not in ALLOWED_INTERVALS:
        raise ValueError(f"Интервал должен быть один из {ALLOWED_INTERVALS}")
    if len(days) != 7 or any(c not in "01" for c in days):
        raise ValueError("Дни недели заданы неверно")
    if "1" not in days:
        raise ValueError("Выберите хотя бы один день")
    if not (0 <= sound_id < len(SOUNDS)):
        raise ValueError("Неизвестный звук")


def alarm_points(start_time: str, end_time: str, interval_minutes: int,
                 days: str) -> list:
    """Точки срабатывания внутри одного дня: startTime + k·interval ≤ endTime.

    Возвращает список минут с полуночи.
    """
    start = parse_time(start_time)
    end = parse_time(end_time)
    points = []
    t = start
    while t <= end:
        points.append(t)
        t += interval_minutes
    return points


def schedule_for_day(alarm: dict, day_date) -> list:
    """Срабатывания для конкретной даты: [] если день не отмечен."""
    if not alarm.get("enabled", 1):
        return []
    if alarm["days"][day_date.weekday()] != "1":
        return []
    return alarm_points(alarm["start_time"], alarm["end_time"],
                        alarm["interval_minutes"], alarm["days"])


def format_schedule(alarm: dict) -> str:
    """Человекочитаемая строка: 'Будни · 11:00–20:00 · каждый час'."""
    selected = [DAY_NAMES[i] for i, c in enumerate(alarm["days"]) if c == "1"]
    if len(selected) == 7:
        days_txt = "Каждый день"
    elif selected == ["Пн", "Вт", "Ср", "Чт", "Пт"]:
        days_txt = "Будни"
    elif selected == ["Сб", "Вс"]:
        days_txt = "Выходные"
    else:
        days_txt = "·".join(selected)
    step = alarm["interval_minutes"]
    if step == 60:
        step_txt = "каждый час"
    else:
        step_txt = f"каждые {step} мин"
    return f"{days_txt} · {alarm['start_time']}–{alarm['end_time']} · {step_txt}"


def next_occurrence(alarm: dict, now: datetime = None) -> datetime:
    """Ближайшее будущее срабатывание (локальное время)."""
    now = now or datetime.now()
    for offset in range(0, 8):  # сегодня..+7 дней
        day = (now + timedelta(days=offset)).date()
        for minute in schedule_for_day(alarm, day):
            point = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute)
            if point > now:
                return point
    raise ValueError("Нет будущих срабатываний (пустое расписание)")
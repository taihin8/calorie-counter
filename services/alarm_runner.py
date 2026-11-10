"""Планировщик будильников: опрос точек срабатывания и вызов звонка.

Работает в фоновом потоке рядом с UI: сам звук и диалог показывает `on_ring`.
Пропущенные точки (приложение было закрыто) не навёрстываются — окно `GRACE`.
"""
import threading
import time
from datetime import datetime, timedelta

from services.alarm_service import alarm_points

CHECK_EVERY = 20               # период опроса, с
GRACE = timedelta(seconds=90)  # насколько «старая» точка ещё считается текущей


def due_point(alarm: dict, now: datetime = None):
    """Последняя точка расписания в окне [now-GRACE, now] или None."""
    now = now or datetime.now()
    if not alarm.get("enabled", 1):
        return None
    if alarm["days"][now.weekday()] != "1":
        return None
    base = datetime.combine(now.date(), datetime.min.time())
    found = None
    for minute in alarm_points(alarm["start_time"], alarm["end_time"],
                               alarm["interval_minutes"], alarm["days"]):
        point = base + timedelta(minutes=minute)
        if now - GRACE <= point <= now:
            found = point
    return found


def should_fire(alarm: dict, point: datetime) -> bool:
    """Точка ещё не звонила: last_fired строго раньше неё."""
    last = alarm.get("last_fired")
    if not last:
        return True
    try:
        return datetime.fromisoformat(last) < point
    except ValueError:
        return True


def find_due(alarms, now: datetime = None):
    """Первая пара (будильник, точка), которую пора звонить."""
    now = now or datetime.now()
    for alarm in alarms:
        point = due_point(alarm, now)
        if point and should_fire(alarm, point):
            return alarm, point
    return None


class AlarmRunner:
    """Опрашивает будильники пользователя и зовёт on_ring(alarm, point)."""

    def __init__(self, user_id, on_ring, interval=CHECK_EVERY):
        self.user_id = user_id
        self.on_ring = on_ring
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(self.interval):
            try:
                self._tick()
            except Exception:
                # сбой опроса не должен убивать поток: ждём следующий цикл
                pass

    def _tick(self):
        from database import get_alarms, mark_alarm_fired
        alarms = get_alarms(self.user_id)
        found = find_due(alarms)
        if not found:
            return
        alarm, point = found
        # отмечаем до звонка: повторный тик не позвонит второй раз
        mark_alarm_fired(alarm["id"], point.isoformat(timespec="seconds"))
        self.on_ring(alarm, point)

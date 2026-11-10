"""Планировщик напоминаний: проверка дат и показ всплывающего окна.

Работает в фоновом потоке рядом с UI. Проверяет раз в час (и сразу при старте),
поэтому приложение, оставленное открытым на ночь, покажет напоминание утром.

Стадии «за день» и «в день» независимы: отметка хранится как «стадия:дата»,
поэтому вчерашнее «за день» не глушит сегодняшнее «в день».
"""
import threading
from datetime import date

from services.reminder_service import due_reminders

CHECK_EVERY = 3600   # раз в час; при старте проверяем сразу


def pending(reminders, today: date = None):
    """Кому и какую стадию показать сейчас: [(напоминание, стадия)]."""
    today = today or date.today()
    out = []
    for reminder, stage in due_reminders(reminders, today):
        shown = reminder.get("last_stage") or ""
        # отметка «стадия:дата» — повторно ту же стадию в тот же день не показываем
        if shown != f"{stage}:{today.isoformat()}":
            out.append((reminder, stage))
    return out


class ReminderRunner:
    """Опрашивает напоминания пользователя и зовёт on_due(reminder, stage)."""

    def __init__(self, user_id, on_due, interval=CHECK_EVERY):
        self.user_id = user_id
        self.on_due = on_due
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
        # первый проход сразу: приложение могли открыть уже после даты
        try:
            self._tick()
        except Exception:
            pass
        while not self._stop.wait(self.interval):
            try:
                self._tick()
            except Exception:
                # сбой проверки не должен убивать поток
                pass

    def _tick(self):
        from database import get_reminders, mark_reminder_shown
        reminders = get_reminders(self.user_id)
        for reminder, stage in pending(reminders):
            # отмечаем до показа: повторный тик не покажет окно второй раз
            mark_reminder_shown(reminder["id"], f"{stage}:{date.today().isoformat()}")
            self.on_due(reminder, stage)

"""Нативные уведомления Android: напоминания приходят, даже если приложение закрыто.

Пакет `flet_android_notifications` необязателен: если его нет (десктоп, веб,
старая сборка), модуль молча выключается — приложение продолжает работать на
всплывающих окнах.
"""
import sys

# стадии: за день до даты и в саму дату
LEAD_DAYS = 1


def _log(message):
    try:
        print(f"[notifications] {message}", file=sys.stderr, flush=True)
    except Exception:
        pass


class ReminderNotifications:
    """Планирует системные уведомления по напоминаниям пользователя."""

    def __init__(self, page, user_id):
        self.page = page
        self.user_id = user_id
        self.service = None
        self.enabled = False
        self.exact = False   # разрешены ли точные будильники (Android 12+)

    def start(self):
        """Подключает сервис и запрашивает разрешения. Вызывать в UI-потоке."""
        try:
            from flet_android_notifications import FletAndroidNotifications
        except Exception as ex:
            _log(f"пакет недоступен: {type(ex).__name__}")
            return False
        try:
            self.service = FletAndroidNotifications()
            self.enabled = True
            self.page.run_task(self._setup)
            return True
        except Exception as ex:
            _log(f"не удалось создать сервис: {type(ex).__name__}: {ex}")
            self.enabled = False
            return False

    async def _setup(self):
        """Разрешения и канал: без них Android 13+ молча глотает уведомления."""
        try:
            await self.service.request_permissions()
        except Exception as ex:
            _log(f"разрешения: {type(ex).__name__}: {ex}")
        try:
            await self.service.create_notification_channel(
                "reminders", "Напоминания",
                channel_description="Памятные дни и дни рождения",
                importance="high", play_sound=True, enable_vibration=True)
        except Exception as ex:
            _log(f"канал: {type(ex).__name__}: {ex}")
        # точный режим: неточный даёт окно до часа, и напоминание опаздывает
        try:
            if not await self.service.can_schedule_exact_notifications():
                await self.service.request_exact_alarm_permission()
            self.exact = True
        except Exception as ex:
            _log(f"точные будильники: {type(ex).__name__}: {ex}")
        self.reschedule()

    def reschedule(self):
        """Пересоздаёт все уведомления по текущим напоминаниям."""
        if not self.enabled:
            return
        self.page.run_task(self._reschedule)

    async def _reschedule(self):
        try:
            from database import get_reminders
            from services.reminder_service import next_occurrence
            reminders = get_reminders(self.user_id)
        except Exception as ex:
            _log(f"чтение напоминаний: {ex}")
            return
        try:
            await self.service.cancel_all()
        except Exception as ex:
            _log(f"отмена старых: {type(ex).__name__}")
        for reminder in reminders:
            try:
                await self._schedule_one(reminder)
            except Exception as ex:
                _log(f"напоминание {reminder.get('id')}: {type(ex).__name__}: {ex}")

    async def _schedule_one(self, reminder):
        """Два уведомления: за день до даты и в саму дату."""
        from services.reminder_service import next_fire_time
        annual = bool(reminder.get("annual", 1))
        base_id = int(reminder["id"]) * 2
        body = reminder["text"]
        for offset, stage, label in ((LEAD_DAYS, "lead", "завтра"),
                                     (0, "day", "сегодня")):
            # ближайшее будущее время: прошедшее сегодня переносится на след. год
            when = next_fire_time(reminder["remind_date"], annual, offset)
            if when is None:
                continue
            await self.service.schedule_notification(
                base_id + (0 if stage == "lead" else 1),
                f"🎂 {body}",
                f"Памятный день {label}",
                when,
                channel_id="reminders",
                channel_name="Напоминания",
                importance="high",
                play_sound=True,
                enable_vibration=True,
                # точное время, если система разрешила; иначе окно до часа
                schedule_mode="exact_allow_while_idle" if self.exact
                              else "inexact_allow_while_idle",
            )

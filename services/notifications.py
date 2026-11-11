"""Нативные уведомления Android: напоминания и удержание будильника.

Пакет `flet_android_notifications` необязателен: если его нет (десктоп, веб,
старая сборка), модуль молча выключается — приложение продолжает работать на
всплывающих окнах.

Зачем foreground-сервис: при сворачивании Android морозит приложение
(`isFrozen=true`, состояние CACHED), и поток планировщика будильника встаёт —
звонок не срабатывает. Сервис держит процесс активным, пока включён хотя бы
один будильник.
"""
import sys

# стадии напоминаний: за день до даты и в саму дату
LEAD_DAYS = 1
# id уведомления сервиса: 0 недопустим
SERVICE_ID = 1000


def _log(message):
    try:
        print(f"[notifications] {message}", file=sys.stderr, flush=True)
    except Exception:
        pass


def service_needed(alarms) -> bool:
    """Нужен ли foreground-сервис: включён хотя бы один будильник."""
    return any(bool(a.get("enabled", 1)) for a in alarms)


class NativeNotifications:
    """Планирует системные уведомления и держит процесс для будильника."""

    def __init__(self, page, user_id):
        self.page = page
        self.user_id = user_id
        self.service = None
        self.enabled = False
        self.exact = False        # разрешены ли точные будильники (Android 12+)
        self.service_running = False

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
        """Разрешения и каналы: без них Android 13+ молча глотает уведомления."""
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
        await self._refresh()

    def refresh(self):
        """Пересоздаёт уведомления и синхронизирует сервис будильника."""
        if not self.enabled:
            return
        self.page.run_task(self._refresh)

    async def _refresh(self):
        await self._reschedule()
        await self._sync_service()

    # ---------- Напоминания ----------

    async def _reschedule(self):
        try:
            from database import get_reminders
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

    # ---------- Будильник: удержание процесса ----------

    async def _sync_service(self):
        """Включает сервис при включённых будильниках и выключает без них."""
        try:
            from database import get_alarms
            needed = service_needed(get_alarms(self.user_id))
        except Exception as ex:
            _log(f"чтение будильников: {ex}")
            return
        if needed == self.service_running:
            return                      # состояние уже верное — не дёргаем Android
        try:
            if needed:
                await self.service.start_foreground_service(
                    SERVICE_ID, "Будильник включён", "Следит за расписанием",
                    foreground_service_types=["special_use"],
                    channel_id="alarm_service", channel_name="Будильник",
                    channel_description="Удержание будильника в фоне",
                    # важность low и silent: уведомление не должно звучать
                    # и мешать, его задача — держать процесс живым
                    importance="low", play_sound=False, enable_vibration=False,
                    ongoing=True, auto_cancel=False, silent=True,
                )
            else:
                await self.service.stop_foreground_service()
            self.service_running = needed
        except Exception as ex:
            _log(f"сервис будильника: {type(ex).__name__}: {ex}")

"""Нативные уведомления Android: напоминания и удержание будильника.

Пакет `flet_android_notifications` необязателен: если его нет (десктоп, веб,
старая сборка), модуль молча выключается — приложение продолжает работать на
всплывающих окнах.

Зачем foreground-сервис: при сворачивании Android морозит приложение
(`isFrozen=true`, состояние CACHED), и поток планировщика будильника встаёт —
звонок не срабатывает. Сервис держит процесс активным, пока включён хотя бы
один будильник.
"""
import json
import sys

# стадии напоминаний: за день до даты и в саму дату
LEAD_DAYS = 1
# id уведомления сервиса: 0 недопустим
SERVICE_ID = 1000
# id уведомлений будильника начинаются отсюда, чтобы не совпасть с напоминаниями
ALARM_ID_BASE = 2000
# префикс payload: по нему узнаём, что нажали именно уведомление будильника
ALARM_PREFIX = "alarm:"


def alarm_payload(alarm_id, point_iso: str) -> str:
    """Метка уведомления будильника: id и время срабатывания."""
    return f"{ALARM_PREFIX}{alarm_id}:{point_iso}"


def parse_alarm_payload(payload: str):
    """(id будильника, время) из метки или None, если метка чужая."""
    if not payload or not payload.startswith(ALARM_PREFIX):
        return None
    try:
        rest = payload[len(ALARM_PREFIX):]
        alarm_id, point_iso = rest.split(":", 1)
        return int(alarm_id), point_iso
    except (ValueError, AttributeError):
        return None


def _log(message):
    try:
        print(f"[notifications] {message}", file=sys.stderr, flush=True)
    except Exception:
        pass


def payload_from(value) -> str:
    """payload из события или ответа плагина.

    Dart присылает JSON-строку, но часть вызовов отдаёт готовый словарь —
    поддерживаем оба вида, иначе нажатие «терялось».
    """
    if isinstance(value, dict):
        return str(value.get("payload") or "")
    if isinstance(value, str):
        text = value.strip()
        if not text.startswith("{"):
            return ""
        try:
            obj = json.loads(text)
        except (ValueError, TypeError):
            return ""
        if isinstance(obj, dict):
            return str(obj.get("payload") or "")
    return ""


def service_needed(alarms) -> bool:
    """Нужен ли foreground-сервис: включён хотя бы один будильник."""
    return any(bool(a.get("enabled", 1)) for a in alarms)


class NativeNotifications:
    """Планирует системные уведомления и держит процесс для будильника."""

    def __init__(self, page, user_id, on_alarm_tap=None):
        self.page = page
        self.user_id = user_id
        # что делать, когда нажали уведомление будильника
        self.on_alarm_tap = on_alarm_tap
        self.service = None
        self.enabled = False
        self.exact = False        # разрешены ли точные будильники (Android 12+)
        self.service_running = False
        # уже обработанные метки: возобновление приложения не должно звонить снова
        self._handled = []

    def start(self):
        """Подключает сервис и запрашивает разрешения. Вызывать в UI-потоке."""
        try:
            from flet_android_notifications import FletAndroidNotifications
        except Exception as ex:
            _log(f"пакет недоступен: {type(ex).__name__}")
            return False
        try:
            # обработчик передаём при создании: назначение после создания
            # могло не дойти до Flutter-стороны, и нажатие терялось
            self.service = FletAndroidNotifications(
                on_notification_tap=self._handle_tap)
            self.enabled = True
            self.page.run_task(self._setup)
            return True
        except Exception as ex:
            _log(f"не удалось создать сервис: {type(ex).__name__}: {ex}")
            self.enabled = False
            return False

    async def _bounded(self, coro, what: str, timeout: float = 3.0):
        """Ждёт ответ плагина не дольше timeout.

        Часть запросов открывает системный экран настроек. Если его не закрыть,
        ответ может не прийти вовсе — без таймаута настройка зависала, и до
        планирования уведомлений дело не доходило.
        """
        import asyncio
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except Exception as ex:
            _log(f"{what}: {type(ex).__name__}")
            return None

    async def _setup(self):
        """Разрешения, каналы и планирование уведомлений."""
        await self._bounded(self.service.request_permissions(), "разрешения")
        await self._bounded(
            self.service.create_notification_channel(
                "reminders", "Напоминания",
                channel_description="Памятные дни и дни рождения",
                importance="high", play_sound=True, enable_vibration=True),
            "канал напоминаний")
        # канал будильника: со звуком и высокой важностью, иначе уведомление
        # приходит «молча» и звонок не слышно
        await self._bounded(
            self.service.create_notification_channel(
                "alarms", "Будильник",
                channel_description="Звонок будильника",
                importance="high", play_sound=True, enable_vibration=True),
            "канал будильника")
        # проверка точных будильников — обычный запрос, экран не открывает
        try:
            allowed = await self._bounded(
                self.service.can_schedule_exact_notifications(), "проверка точных")
            self.exact = bool(allowed)
        except Exception as ex:
            _log(f"точные будильники: {type(ex).__name__}")
        # планируем ДО запросов, которые открывают системные экраны
        await self._refresh()
        # просьбы, открывающие настройки Android: ограничены по времени
        if not self.exact:
            await self._bounded(self.service.request_exact_alarm_permission(),
                                "запрос точных будильников")
        await self._bounded(self.service.request_full_screen_intent_permission(),
                            "полноэкранное окно")

    def refresh(self):
        """Пересоздаёт уведомления и синхронизирует сервис будильника."""
        if not self.enabled:
            return
        self.page.run_task(self._refresh)

    async def _refresh(self):
        await self._reschedule()
        await self._schedule_alarms()
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

    # ---------- Нажатие по уведомлению будильника ----------

    def _handle_tap(self, e=None):
        """Система подняла приложение по уведомлению — звоним.

        Dart присылает событие по-разному (словарь или JSON-строка), поэтому
        разбираем оба вида — иначе нажатие молча терялось.
        """
        try:
            payload = payload_from(getattr(e, "data", None))
        except Exception as ex:
            _log(f"нажатие: {type(ex).__name__}: {ex}")
            return
        self.ring_by_payload(payload)

    async def check_launch(self):
        """Звонит, если приложение запустили нажатием по уведомлению.

        Нужно при холодном старте: событие нажатия тогда ещё некому слушать.
        """
        try:
            details = await self.service.get_notification_app_launch_details()
            if not details.get("did_notification_launch_app"):
                return
            self.ring_by_payload(payload_from(details.get("notification_response")))
        except Exception as ex:
            _log(f"запуск по уведомлению: {type(ex).__name__}: {ex}")

    def ring_by_payload(self, payload: str):
        """Звонит по метке уведомления; чужие метки игнорирует."""
        parsed = parse_alarm_payload(payload)
        if not parsed:
            return
        if payload in self._handled:
            return                    # это срабатывание уже отзвонили
        self._handled.append(payload)
        del self._handled[:-20]       # держим только последние метки
        alarm_id, point_iso = parsed
        try:
            from datetime import datetime
            from database import get_alarm, mark_alarm_fired
            alarm = get_alarm(alarm_id)
            if not alarm:
                _log(f"будильник {alarm_id} не найден")
                return
            point = datetime.fromisoformat(point_iso)
            # отметку ставим до звонка: повторное нажатие не позвонит снова
            mark_alarm_fired(alarm_id, point.isoformat(timespec="seconds"))
            if self.on_alarm_tap:
                self.on_alarm_tap(alarm, point)
        except Exception as ex:
            _log(f"звонок по уведомлению: {type(ex).__name__}: {ex}")

    # ---------- Будильник: системное уведомление в момент срабатывания ----------

    async def _schedule_alarms(self):
        """Ставит уведомление на ближайшее срабатывание каждого будильника.

        Приложение может быть выгружено системой — тогда поток планировщика
        не работает. Уведомление ставит сама система, и по нажатию открывает
        приложение: окно звонка запускается уже в живом процессе.
        """
        try:
            from database import get_alarms
            alarms = get_alarms(self.user_id)
        except Exception as ex:
            _log(f"чтение будильников: {ex}")
            return
        for alarm in alarms:
            try:
                await self._schedule_alarm_one(alarm)
            except Exception as ex:
                _log(f"будильник {alarm.get('id')}: {type(ex).__name__}: {ex}")

    async def _schedule_alarm_one(self, alarm):
        """Уведомление на ближайшую точку расписания будильника."""
        from services.alarm_service import next_occurrence, format_schedule
        if not alarm.get("enabled", 1):
            return
        try:
            point = next_occurrence(alarm)
        except Exception as ex:
            _log(f"расписание будильника: {type(ex).__name__}")
            return
        await self.service.schedule_notification(
            ALARM_ID_BASE + int(alarm["id"]),
            f"⏰ Будильник · {point.strftime('%H:%M')}",
            format_schedule(alarm),
            point,
            payload=alarm_payload(alarm["id"], point.isoformat(timespec="minutes")),
            channel_id="alarms", channel_name="Будильник",
            channel_description="Звонок будильника",
            importance="high", play_sound=True, enable_vibration=True,
            category="alarm", full_screen_intent=True,
            # точное время: иначе система может позвонить с задержкой до часа
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

"""Экран звонка: играет мелодию, ждёт «Стоп» или гасит звук через минуту.

Диалог показываем ПЕРВЫМ, а плеер создаём следом: на Android создание
audio-сервиса может занять время или не удаться, но звонок пользователь
обязан увидеть в любом случае.

Звук идёт по каналу будильника (USAGE_ALARM, патч tools/patch_flet_audio.py),
поэтому слышен даже при выключенном или минимальном медиа-звуке.
"""
import threading

import flet as ft

from services.alarm_service import SOUNDS, format_schedule
from services.sounds import sound_bytes

RING_SECONDS = 60      # сколько играет мелодия (по спецификации)
RAMP_SECONDS = 8       # нарастание громкости от тихого к полному
START_VOLUME = 0.25    # слышно сразу, но не пугает

# держим плееры живыми, пока играют: без ссылки сервис выгружается сборщиком
_active = []


def show_ring(page: ft.Page, alarm: dict, point):
    """Показывает диалог звонка и запускает звук. Возвращает управление сразу."""
    stopped = threading.Event()
    state = {"player": None, "wake": None}
    note = ft.Text("", size=11, color=ft.Colors.ORANGE)

    def finish(e=None):
        if stopped.is_set():
            return
        stopped.set()
        player = state["player"]
        if player is not None:
            page.run_task(_pause, player)
            if player in _active:
                _active.remove(player)
        wake = state["wake"]
        if wake is not None:
            page.run_task(_release_wake, wake)
        page.pop_dialog()

    def init_audio():
        """Плеер и удержание экрана — после показа диалога: сбой звука не скроет звонок."""
        try:
            import flet_audio as fa
            data = sound_bytes(alarm.get("sound_id", 0))
            player = fa.Audio(src=data, autoplay=True, volume=START_VOLUME,
                              release_mode=fa.ReleaseMode.LOOP)
            state["player"] = player
            _active.append(player)
        except Exception as ex:
            note.value = f"Звук недоступен: {type(ex).__name__}"
            try:
                page.update()
            except Exception:
                pass
        # экран не должен погаснуть, пока звенит
        try:
            wake = ft.Wakelock()
            state["wake"] = wake
            page.run_task(_hold_wake, wake)
        except Exception:
            pass

    def ramp():
        """Плавно поднимаем громкость, пока не остановили."""
        for step in range(RAMP_SECONDS):
            if stopped.wait(1):
                return
            player = state["player"]
            if player is None:
                continue
            volume = min(1.0, START_VOLUME + (1 - START_VOLUME) * (step + 1) / RAMP_SECONDS)
            try:
                page.run_thread(_set_volume, player, volume)
            except Exception:
                return

    def bring_to_front():
        """Выводим окно поверх других: будильник должен быть виден."""
        try:
            page.run_task(_to_front, page)
        except Exception:
            pass

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"⏰ Будильник · {point.strftime('%H:%M')}"),
        content=ft.Column([
            ft.Text(format_schedule(alarm), size=13),
            ft.Text(f"Звук: {_sound_name(alarm.get('sound_id', 0))}", size=12,
                    color=ft.Colors.GREY),
            note,
        ], spacing=4, tight=True),
        actions=[ft.ElevatedButton("Стоп", on_click=finish)],
    )
    page.show_dialog(dialog)

    page.run_thread(init_audio)
    bring_to_front()
    threading.Thread(target=ramp, daemon=True).start()
    timer = threading.Timer(RING_SECONDS, finish)
    timer.daemon = True
    timer.start()


async def _to_front(page):
    try:
        await page.window.to_front()
    except Exception:
        pass  # на мобильных вызов может быть не поддержан


async def _hold_wake(wake):
    try:
        await wake.enable()
    except Exception:
        pass


async def _release_wake(wake):
    try:
        await wake.disable()
    except Exception:
        pass


def _sound_name(sound_id):
    """Имя трека по id; SOUNDS — список, id может выйти за границы."""
    return SOUNDS[sound_id] if 0 <= sound_id < len(SOUNDS) else ""


def _set_volume(player, volume):
    try:
        player.volume = volume
        player.update()
    except Exception:
        pass


async def _pause(player):
    try:
        await player.pause()
    except Exception:
        pass

"""Редактор будильника: дни недели (с пресетами), окно, интервал, звук."""
import flet as ft
from database import add_alarm, update_alarm, get_alarm, delete_alarm
from services.alarm_service import (
    validate_alarm, DAY_PRESETS, DAY_NAMES, SOUNDS, ALLOWED_INTERVALS,
)


def alarm_editor_dialog(page: ft.Page, user_id: int, alarm_id=None, on_saved=None):
    """Диалог создания (alarm_id=None) или редактирования будильника."""
    alarm = get_alarm(alarm_id) if alarm_id else None
    days_state = list(alarm["days"]) if alarm else list(DAY_PRESETS["weekdays"])
    error = ft.Text("", color=ft.Colors.RED, size=12)

    # value у TimePicker长 'HH:mm:ss', берём первые 5 символов
    start_time = ft.TextField(label="Начало (ЧЧ:ММ)",
                              value=alarm["start_time"] if alarm else "09:00")
    end_time = ft.TextField(label="Окончание (ЧЧ:ММ)",
                            value=alarm["end_time"] if alarm else "10:00")

    def apply_preset(key):
        nonlocal days_state
        days_state = list(DAY_PRESETS[key])
        render_days()
        page.update()

    def toggle_day(i):
        days_state[i] = "1" if days_state[i] == "0" else "0"
        render_days()
        page.update()

    days_row = ft.Row(wrap=True, spacing=4, run_spacing=4)

    def render_days():
        days_row.controls.clear()
        for i, name in enumerate(DAY_NAMES):
            days_row.controls.append(
                ft.Chip(
                    label=ft.Text(name),
                    selected=days_state[i] == "1",
                    on_click=lambda e, idx=i: toggle_day(idx),
                )
            )

    interval = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value=str(s), label=f"{s} мин")
            for s in ALLOWED_INTERVALS
        ], wrap=True),
        value=str(alarm["interval_minutes"]) if alarm else "60",
    )

    sound = ft.RadioGroup(
        content=ft.Column([ft.Radio(value=str(i), label=name)
                           for i, name in enumerate(SOUNDS)]),
        value=str(alarm["sound_id"]) if alarm else "0",
    )

    preset_row = ft.Row([
        ft.TextButton("Будни", on_click=lambda e: apply_preset("weekdays")),
        ft.TextButton("Выходные", on_click=lambda e: apply_preset("weekends")),
        ft.TextButton("Каждый день", on_click=lambda e: apply_preset("every_day")),
    ], spacing=4)

    def save(e):
        try:
            validate_alarm(start_time.value, end_time.value,
                           int(interval.value), "".join(days_state),
                           int(sound.value))
        except ValueError as ex:
            error.value = str(ex)
            page.update()
            return
        page.pop_dialog()
        if alarm_id:
            update_alarm(alarm_id, "".join(days_state), start_time.value,
                         end_time.value, int(interval.value), int(sound.value),
                         alarm["enabled"])
        else:
            add_alarm(user_id, "".join(days_state), start_time.value,
                      end_time.value, int(interval.value), int(sound.value))
        if on_saved:
            on_saved()

    def remove(e):
        page.pop_dialog()
        if alarm_id:
            delete_alarm(alarm_id)
        if on_saved:
            on_saved()

    render_days()
    actions = [
        ft.TextButton("Отмена", on_click=lambda e: page.pop_dialog()),
        ft.ElevatedButton("Сохранить", on_click=save),
    ]
    if alarm_id:
        actions.insert(0, ft.TextButton("Удалить", on_click=remove))

    dialog = ft.AlertDialog(
        title=ft.Text("Будильник" if not alarm_id else "Изменить будильник"),
        content=ft.Column([
            preset_row,
            days_row,
            ft.Divider(height=8),
            ft.Row([start_time, end_time], spacing=4),
            ft.Text("Интервал:", size=13),
            interval,
            ft.Text("Звук:", size=13),
            sound,
            error,
        ], spacing=6, tight=True, scroll=ft.ScrollMode.AUTO),
        actions=actions,
    )
    page.show_dialog(dialog)
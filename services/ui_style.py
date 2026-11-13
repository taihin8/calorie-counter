"""Оформление: единые карточки и заголовки разделов.

Один файл на все экраны, чтобы списки продуктов, заметок и напоминаний
выглядели одинаково. Цвета берём из темы (SURFACE_*, OUTLINE_*), поэтому
оформление работает и на светлой, и на тёмной теме.
"""
import flet as ft

# отступы и радиусы
CARD_PAD = 12
CARD_RADIUS = 14
ROW_PAD = 10
ROW_RADIUS = 12


def _shadow(alpha=0.07):
    """Мягкая тень: карточки отделяются от фона даже на близких тонах."""
    return ft.BoxShadow(
        blur_radius=10, spread_radius=0,
        color=ft.Colors.with_opacity(alpha, ft.Colors.BLACK),
        offset=ft.Offset(0, 2),
    )


def card(content, *, padding=CARD_PAD, radius=CARD_RADIUS, expand=False):
    """Карточка с фоном из темы, тонкой рамкой и лёгкой тенью."""
    return ft.Container(
        content=content,
        padding=padding,
        border_radius=radius,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        shadow=_shadow(),
        expand=expand,
    )


def row_card(content, *, expand=False):
    """Карточка для одной строки списка: компактнее, чем block."""
    return ft.Container(
        content=content,
        padding=ft.Padding.symmetric(horizontal=ROW_PAD, vertical=8),
        border_radius=ROW_RADIUS,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        shadow=_shadow(0.05),
        expand=expand,
    )


def section_title(text, trailing=None):
    """Заголовок раздела: текст слева, необязательная кнопка справа."""
    controls = [ft.Text(text, size=15, weight=ft.FontWeight.W_600, expand=True)]
    if trailing is not None:
        controls.append(trailing)
    return ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def shade(page, light_color, dark_color):
    """Оттенок под тему: на светлой берём тёмный вариант, на тёмной — светлый.

    Цветной текст среднего тона (GREEN, RED) на светлом фоне даёт контраст
    около 1.7:1 и читается плохо, поэтому в светлой теме нужен тёмный оттенок.
    """
    try:
        is_dark = page.theme_mode == ft.ThemeMode.DARK
    except Exception:
        is_dark = False
    return dark_color if is_dark else light_color


def ok_color(page):
    """Цвет «всё хорошо» (в норме калорий)."""
    return shade(page, ft.Colors.GREEN_800, ft.Colors.GREEN_300)


def warn_color(page):
    """Цвет предупреждения (перебор калорий)."""
    return shade(page, ft.Colors.RED_700, ft.Colors.RED_300)


def hint(text):
    """Мелкая подпись под заголовком."""
    return ft.Text(text, size=11, color=ft.Colors.ON_SURFACE_VARIANT)


def empty(text):
    """Заглушка для пустого списка."""
    return ft.Container(
        content=ft.Text(text, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        padding=ft.Padding.symmetric(horizontal=4, vertical=10),
    )

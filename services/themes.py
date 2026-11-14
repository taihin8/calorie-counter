"""Темы оформления. Хранится по имени; применение — в один вызов."""
import flet as ft

# имя -> (название для меню, theme_mode, seed цвета)
# seed задаёт палитру Material 3: от него зависят основные цвета, индикатор
# вкладок, кнопки и оттенки поверхностей. Раньше у «Светлой» и «Синей» был
# один и тот же BLUE, поэтому разницы не было видно.
THEMES = {
    'light':    ('Светлая',    ft.ThemeMode.LIGHT, ft.Colors.TEAL),
    'graphite': ('Графит',     ft.ThemeMode.DARK,  ft.Colors.BLUE_GREY),
    'green':    ('Зелёная',    ft.ThemeMode.LIGHT, ft.Colors.GREEN),
    'blue':     ('Синяя',      ft.ThemeMode.LIGHT, ft.Colors.BLUE),
    'violet':   ('Фиолетовая', ft.ThemeMode.LIGHT, ft.Colors.DEEP_PURPLE),
    'warm':     ('Тёплая',     ft.ThemeMode.LIGHT, ft.Colors.ORANGE),
}

DEFAULT_THEME = 'light'


def theme_seed(name: str) -> str:
    """Seed-цвет темы (для цветной метки в меню выбора)."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])[2]


def apply_theme(page: ft.Page, name: str):
    name = name if name in THEMES else DEFAULT_THEME
    mode, seed = THEMES[name][1], THEMES[name][2]
    page.theme_mode = mode
    page.theme = ft.Theme(color_scheme_seed=seed)
    page.update()

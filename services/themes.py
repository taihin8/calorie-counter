"""Темы оформления. Хранится по имени; применение — в один вызов."""
import flet as ft

# имя -> (название для меню, theme_mode, seed цвета или None)
THEMES = {
    'light':    ('Светлая', ft.ThemeMode.LIGHT, None),
    'graphite': ('Графит',  ft.ThemeMode.DARK,  ft.Colors.BLUE_GREY),
    'green':    ('Зелёная', ft.ThemeMode.LIGHT, ft.Colors.GREEN),
    'blue':     ('Синяя',   ft.ThemeMode.LIGHT, ft.Colors.BLUE),
}

def apply_theme(page: ft.Page, name: str):
    name = name if name in THEMES else 'light'
    mode, seed = THEMES[name][1], THEMES[name][2]
    page.theme_mode = mode
    if seed:
        page.theme = ft.Theme(color_scheme_seed=seed)
    else:
        page.theme = None
    page.update()
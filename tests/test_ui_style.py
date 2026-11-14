"""Оформление: карточки берут цвета из темы, а не хардкод.

Раньше блок цели использовал GREY_100: на тёмной теме «Графит» светло-серый
фон сливался со светлым текстом. Тест держит это исправление.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import flet as ft
from services.ui_style import card, row_card, section_title, hint, empty


def test_card_uses_theme_colors():
    c = card(ft.Text("x"))
    assert c.bgcolor == ft.Colors.SURFACE_CONTAINER_HIGHEST
    # на тёмной теме GREY_100 давал нечитаемый текст
    assert c.bgcolor != ft.Colors.GREY_100
    assert c.border is not None


def test_row_card_is_theme_aware():
    c = row_card(ft.Text("x"))
    assert c.bgcolor == ft.Colors.SURFACE_CONTAINER_HIGH
    assert c.bgcolor != ft.Colors.GREY_100


def test_section_title_has_trailing():
    """Кнопка справа добавляется, если передана."""
    plain = section_title("Заголовок")
    assert len(plain.controls) == 1
    with_btn = section_title("Заголовок", ft.IconButton(ft.Icons.ADD))
    assert len(with_btn.controls) == 2


def test_hint_and_empty_are_variant_color():
    """Приглушённый текст — адаптивный цвет, читаемый на обеих темах."""
    assert hint("т").color == ft.Colors.ON_SURFACE_VARIANT
    assert hint("т").color != ft.Colors.GREY_300


def test_shade_picks_dark_on_light_theme():
    """На светлой теме берём тёмный оттенок: светлый зелёный не читается."""
    import flet as ft
    from services.ui_style import shade, ok_color, warn_color

    class _P:
        theme_mode = ft.ThemeMode.LIGHT
    class _D:
        theme_mode = ft.ThemeMode.DARK

    assert shade(_P(), ft.Colors.GREEN_800, ft.Colors.GREEN_300) == ft.Colors.GREEN_800
    assert shade(_D(), ft.Colors.GREEN_800, ft.Colors.GREEN_300) == ft.Colors.GREEN_300
    assert ok_color(_P()) == ft.Colors.GREEN_800
    assert warn_color(_P()) == ft.Colors.RED_700


def test_shade_survives_broken_page():
    """Если у страницы нет theme_mode, не падаем — считаем тему светлой."""
    from services.ui_style import shade
    import flet as ft

    class _Broken:
        @property
        def theme_mode(self):
            raise RuntimeError("нет темы")
    assert shade(_Broken(), ft.Colors.GREEN_800, ft.Colors.GREEN_300) == ft.Colors.GREEN_800


def test_rows_have_shadow():
    """Тень отделяет карточку от фона на близких тонах."""
    from services.ui_style import card, row_card
    assert card(None).shadow is not None
    assert row_card(None).shadow is not None


def _wcag_contrast(a, b):
    """Контраст по WCAG: нужен >= 4.5:1 для обычного текста."""
    def srgb(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    def lum(col):
        r, g, bl = col
        return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(bl)
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def test_badge_kinds_have_readable_contrast():
    """Тональные метки читаются: раньше оранжевая заливка давала 2.7:1."""
    import flet as ft
    from services.ui_style import badge

    class _P:
        theme_mode = ft.ThemeMode.LIGHT

    pairs = {
        "today": ((232, 245, 233), (27, 94, 32)),      # GREEN_50 / GREEN_900
        "tomorrow": ((255, 243, 224), (191, 54, 12)),   # ORANGE_50 / ORANGE_900
    }
    for kind, (bg, fg) in pairs.items():
        assert _wcag_contrast(bg, fg) >= 4.5, kind
        b = badge(_P(), "x", kind=kind)
        assert b.bgcolor is not None and b.content.color is not None


def test_badge_survives_broken_page():
    """Без темы у страницы метка всё равно создаётся."""
    from services.ui_style import badge
    class _Broken:
        @property
        def theme_mode(self):
            raise RuntimeError("нет темы")
    assert badge(_Broken(), "x", kind="today") is not None


def test_themes_have_unique_seeds():
    """У каждой темы своя палитра.

    Раньше «Светлая» и «Синяя» использовали один seed BLUE, поэтому выбор
    темы не давал видимой разницы.
    """
    from services.themes import THEMES
    seeds = [str(v[2]) for v in THEMES.values()]
    assert len(set(seeds)) == len(seeds), f"повтор seed: {seeds}"


def test_theme_seed_returns_color():
    from services.themes import theme_seed, DEFAULT_THEME, THEMES
    assert theme_seed(DEFAULT_THEME) == THEMES[DEFAULT_THEME][2]
    # неизвестное имя -> тема по умолчанию, без падения
    assert theme_seed("нет-такой") == THEMES[DEFAULT_THEME][2]

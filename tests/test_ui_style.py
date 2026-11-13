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

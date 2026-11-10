"""Размер шрифта заметок: хранение по пользователю и валидация."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import database


def _fresh_db(tmp_path):
    database.DB_PATH = str(tmp_path / "t.db")
    database.init_db()


def test_default_note_font(tmp_path):
    """По умолчанию 10 — самое мелкое из допустимых, крупнее можно выбрать."""
    _fresh_db(tmp_path)
    uid = database.add_user("u1", "x")
    assert database.get_note_font_size(uid) == database.DEFAULT_NOTE_FONT == 10
    assert database.NOTE_FONT_SIZES == (10, 12, 14)


def test_adaptive_grey_is_readable(tmp_path):
    """Приглушённый текст — адаптивный цвет, а не GREY_300.

    GREY_300 на светлой теме давал контраст 1.11:1: подписи дат в напоминаниях
    и подсказки в диалогах были практически не видны.
    """
    import flet as ft
    from screens import diary
    assert diary.GREY == ft.Colors.ON_SURFACE_VARIANT
    assert diary.GREY != ft.Colors.GREY_300


def test_old_size_8_falls_back_to_default(tmp_path):
    """У тех, кто выбрал убранный 8, показывается 10, а не ошибка."""
    _fresh_db(tmp_path)
    uid = database.add_user("old8", "x")
    conn = database.get_db()
    conn.execute("UPDATE users SET note_font_size = 8 WHERE id = ?", (uid,))
    conn.commit()
    conn.close()
    assert database.get_note_font_size(uid) == 10


def test_set_and_get_note_font(tmp_path):
    """Выбранный размер сохраняется и переживает повторное чтение."""
    _fresh_db(tmp_path)
    uid = database.add_user("u2", "x")
    for size in database.NOTE_FONT_SIZES:
        database.set_note_font_size(uid, size)
        assert database.get_note_font_size(uid) == size


def test_invalid_note_font_rejected(tmp_path):
    """Мусор не сохраняется: только 8/10/12."""
    _fresh_db(tmp_path)
    uid = database.add_user("u3", "x")
    for bad in (0, 8, 9, 11, 99, -1, 1000):   # 8 убран: слишком мелкий
        try:
            database.set_note_font_size(uid, bad)
            assert False, f"принят недопустимый размер {bad}"
        except ValueError:
            pass
    assert database.get_note_font_size(uid) == database.DEFAULT_NOTE_FONT


def test_note_font_is_per_user(tmp_path):
    """Размер шрифта у каждого пользователя свой."""
    _fresh_db(tmp_path)
    u1 = database.add_user("a", "x")
    u2 = database.add_user("b", "x")
    database.set_note_font_size(u1, 10)
    database.set_note_font_size(u2, 14)
    assert database.get_note_font_size(u1) == 10
    assert database.get_note_font_size(u2) == 14


def test_notes_store_full_text(tmp_path):
    """Длинная заметка хранится целиком — список переносит её, а не режет."""
    _fresh_db(tmp_path)
    uid = database.add_user("c", "x")
    long_text = "Слово " * 60
    database.add_note(uid, long_text, "2026-11-10")
    notes = database.get_notes(uid)
    assert notes[0]["text"] == long_text

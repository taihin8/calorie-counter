"""Размер шрифта напоминаний: своя настройка, независимая от заметок."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import database


def _fresh_db(tmp_path):
    database.DB_PATH = str(tmp_path / "t.db")
    database.init_db()


def test_default_reminder_font(tmp_path):
    _fresh_db(tmp_path)
    uid = database.add_user("r1", "x")
    assert database.get_reminder_font_size(uid) == database.DEFAULT_NOTE_FONT == 10


def test_set_and_get_reminder_font(tmp_path):
    _fresh_db(tmp_path)
    uid = database.add_user("r2", "x")
    for size in database.NOTE_FONT_SIZES:
        database.set_reminder_font_size(uid, size)
        assert database.get_reminder_font_size(uid) == size


def test_invalid_reminder_font_rejected(tmp_path):
    """8 убран: слишком мелкий. Мусор не сохраняется."""
    _fresh_db(tmp_path)
    uid = database.add_user("r3", "x")
    for bad in (0, 8, 9, 11, 99, -1):
        try:
            database.set_reminder_font_size(uid, bad)
            assert False, f"принят недопустимый размер {bad}"
        except ValueError:
            pass
    assert database.get_reminder_font_size(uid) == 10


def test_fonts_are_independent(tmp_path):
    """Шрифт напоминаний не тянет за собой шрифт заметок."""
    _fresh_db(tmp_path)
    uid = database.add_user("r4", "x")
    database.set_note_font_size(uid, 12)
    database.set_reminder_font_size(uid, 14)
    assert database.get_note_font_size(uid) == 12
    assert database.get_reminder_font_size(uid) == 14


def test_old_size_8_falls_back(tmp_path):
    """У выбравших убранную 8 показывается 10, а не ошибка."""
    _fresh_db(tmp_path)
    uid = database.add_user("r5", "x")
    conn = database.get_db()
    conn.execute("UPDATE users SET reminder_font_size = 8 WHERE id = ?", (uid,))
    conn.commit(); conn.close()
    assert database.get_reminder_font_size(uid) == 10

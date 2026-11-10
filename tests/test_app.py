import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_database_imports():
    """Проверяем, что модули импортируются"""
    import database
    assert database is not None

def test_shift_month():
    """Переключение месяца календаря назад/вперёд, включая переход через год."""
    from datetime import datetime
    from screens.diary import _shift_month

    d = datetime(2026, 11, 1)
    assert _shift_month(d, -1).strftime('%Y-%m') == '2026-10'
    assert _shift_month(d, 1).strftime('%Y-%m') == '2026-12'
    assert _shift_month(datetime(2026, 1, 1), -1).strftime('%Y-%m') == '2025-12'
    assert _shift_month(datetime(2026, 12, 1), 1).strftime('%Y-%m') == '2027-01'

def test_open_themes_shows_dialog():
    """Диалог темы должен реально показываться (регрессия: блок висел в open_alarms)."""
    import inspect
    from screens import diary
    src = inspect.getsource(diary.diary_screen)
    head, sep, tail = src.partition("def open_themes(e):")
    body = tail.partition("def open_alarms(e):")[0]
    assert "page.show_dialog(dialog)" in body

def test_init_db():
    """Проверяем создание базы"""
    import database
    import tempfile
    tmp = tempfile.mkdtemp()
    database.DB_PATH = os.path.join(tmp, 'test.db')
    database.init_db()
    assert os.path.exists(database.DB_PATH)
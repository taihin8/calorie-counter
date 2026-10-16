import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_database_imports():
    """Проверяем, что модули импортируются"""
    import database
    assert database is not None

def test_init_db():
    """Проверяем создание базы"""
    import database
    import tempfile
    tmp = tempfile.mkdtemp()
    database.DB_PATH = os.path.join(tmp, 'test.db')
    database.init_db()
    assert os.path.exists(database.DB_PATH)
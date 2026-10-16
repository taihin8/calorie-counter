import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import database
import tempfile

def setup_function():
    # Use temp DB for tests
    tmp = tempfile.mkdtemp()
    database.DB_PATH = os.path.join(tmp, 'test.db')
    database.init_db()

def test_add_and_get_user():
    uid = database.add_user('testuser', 'pass123')
    assert uid is not None
    user = database.get_user('testuser', 'pass123')
    assert user['username'] == 'testuser'

def test_duplicate_user():
    database.add_user('dup', 'p1')
    assert database.add_user('dup', 'p2') is None

def test_wrong_password():
    database.add_user('u', 'correct')
    assert database.get_user('u', 'wrong') is None

def test_add_and_calc_calories():
    uid = database.add_user('cal', 'p')
    database.add_food_entry(uid, 'Яблоко', 52, 200)
    database.add_food_entry(uid, 'Хлеб', 260, 100)
    total = database.get_daily_calories(uid)
    # 52*2 + 260 = 364
    assert total == 364

def test_daily_food_empty_by_default():
    uid = database.add_user('d', 'p')
    assert database.get_daily_food(uid) == []

def test_add_and_get_notes():
    uid = database.add_user('n', 'p')
    database.add_note(uid, 'Тестовая заметка')
    notes = database.get_notes(uid)
    assert len(notes) == 1
    assert notes[0]['text'] == 'Тестовая заметка'

def test_delete_note():
    uid = database.add_user('nd', 'p')
    database.add_note(uid, 'Удалить меня')
    notes = database.get_notes(uid)
    database.delete_note(notes[0]['id'])
    assert database.get_notes(uid) == []

def test_update_note():
    uid = database.add_user('nu', 'p')
    database.add_note(uid, 'Старый текст')
    notes = database.get_notes(uid)
    database.update_note(notes[0]['id'], 'Новый текст')
    notes = database.get_notes(uid)
    assert notes[0]['text'] == 'Новый текст'

def test_delete_food_entry():
    uid = database.add_user('fd', 'p')
    database.add_food_entry(uid, 'Продукт', 100, 100)
    entries = database.get_daily_food(uid)
    database.delete_food_entry(entries[0]['id'])
    assert database.get_daily_food(uid) == []

def test_update_food_entry():
    uid = database.add_user('fu', 'p')
    database.add_food_entry(uid, 'Старое', 100, 100)
    entries = database.get_daily_food(uid)
    database.update_food_entry(entries[0]['id'], 'Новое', 200, 50)
    entries = database.get_daily_food(uid)
    assert entries[0]['product_name'] == 'Новое'
    assert entries[0]['calories'] == 200
    assert entries[0]['grams'] == 50

def test_get_entry_dates():
    uid = database.add_user('gd', 'p')
    # default date
    database.add_food_entry(uid, 'Продукт', 100, 100)
    # another date
    database.add_food_entry(uid, 'Другой', 50, 100, '2026-10-01')
    dates = database.get_entry_dates(uid)
    assert len(dates) == 2

import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'instance', 'app.db')

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS food_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            product_name TEXT NOT NULL,
            calories REAL NOT NULL,
            grams REAL DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()['id']
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user(username, password):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
    conn.close()
    return dict(user) if user else None

def add_food_entry(user_id, product_name, calories, grams=100, entry_date=None):
    entry_date = entry_date or str(date.today())
    conn = get_db()
    conn.execute("INSERT INTO food_entries (user_id, date, product_name, calories, grams) VALUES (?, ?, ?, ?, ?)",
                 (user_id, entry_date, product_name, calories, grams))
    conn.commit()
    conn.close()

def get_daily_food(user_id, entry_date=None):
    entry_date = entry_date or str(date.today())
    conn = get_db()
    rows = conn.execute("SELECT * FROM food_entries WHERE user_id = ? AND date = ? ORDER BY id", (user_id, entry_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_daily_calories(user_id, entry_date=None):
    entry_date = entry_date or str(date.today())
    conn = get_db()
    row = conn.execute("SELECT COALESCE(SUM(calories * grams / 100.0), 0) as total FROM food_entries WHERE user_id = ? AND date = ?", (user_id, entry_date)).fetchone()
    conn.close()
    return row['total']

def add_note(user_id, text, entry_date=None):
    entry_date = entry_date or str(date.today())
    conn = get_db()
    conn.execute("INSERT INTO notes (user_id, text, date) VALUES (?, ?, ?)", (user_id, text, entry_date))
    conn.commit()
    conn.close()

def get_notes(user_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY date DESC, id DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_note(note_id):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

def update_note(note_id, text):
    conn = get_db()
    conn.execute("UPDATE notes SET text = ? WHERE id = ?", (text, note_id))
    conn.commit()
    conn.close()

def delete_food_entry(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM food_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

def update_food_entry(entry_id, product_name, calories, grams):
    conn = get_db()
    conn.execute("UPDATE food_entries SET product_name = ?, calories = ?, grams = ? WHERE id = ?",
                 (product_name, calories, grams, entry_id))
    conn.commit()
    conn.close()

def get_entry_dates(user_id):
    """Возвращает список дат, в которые есть внесённые продукты"""
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT date FROM food_entries WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return [r['date'] for r in rows]

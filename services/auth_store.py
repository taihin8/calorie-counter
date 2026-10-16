"""Запоминает пользователей, входивших на этом устройстве."""
import os
import json

STORE_PATH = os.path.join(os.path.dirname(__file__), '..', 'instance', 'known_users.json')


def _load():
    try:
        with open(STORE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        users = data.get("users", [])
        last = data.get("last")
        return users, last
    except (FileNotFoundError, json.JSONDecodeError):
        return [], None


def _save(users, last):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with open(STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump({"users": users, "last": last}, f, ensure_ascii=False)


def save_last_user(username):
    """Помечает пользователя как последнего и добавляет в список известных."""
    users, _ = _load()
    if username in users:
        users.remove(username)
    users.insert(0, username)
    _save(users, username)


def get_last_user():
    _, last = _load()
    return last


def get_known_users():
    """Все пользователи, входившие на этом устройстве (самый свежий первый)."""
    users, _ = _load()
    return users


def clear_last_user():
    users, _ = _load()
    _save(users, None)
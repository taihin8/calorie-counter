"""Запоминает последнего авторизовавшегося пользователя."""
import os
import json

STORE_PATH = os.path.join(os.path.dirname(__file__), '..', 'instance', 'last_user.json')

def save_last_user(username):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with open(STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump({"username": username}, f)

def get_last_user():
    try:
        with open(STORE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f).get("username")
    except (FileNotFoundError, json.JSONDecodeError):
        return None
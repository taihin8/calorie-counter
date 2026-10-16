import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from services.food_db import search_food, guess_calories

def test_search_exact():
    assert search_food("яблоко") == [("яблоко", 52)]

def test_search_case_insensitive():
    res = search_food("ЯБЛОКО")
    assert res and res[0][0] == "яблоко"

def test_search_partial():
    res = search_food("бана")
    assert ("банан", 89) in res

def test_search_empty():
    assert search_food("") == []
    assert search_food("   ") == []

def test_search_unknown():
    assert search_food("артефактxyz") == []

def test_guess_direct():
    assert guess_calories("яблоко") == 52

def test_guess_multiword():
    # 'хлеб белый нарезной' -> по слову 'хлеб'
    assert guess_calories("хлеб белый нарезной") == 265

def test_guess_unknown():
    assert guess_calories("экзотическое блюдо") is None
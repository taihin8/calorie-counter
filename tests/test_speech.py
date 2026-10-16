import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from services.speech import parse_food_text

def test_parse_with_calories_and_grams():
    name, cal, grams = parse_food_text("яблоко 52 калории на 200 грамм")
    assert name == "яблоко"
    assert cal == 52
    assert grams == 200

def test_parse_with_kcal_word():
    name, cal, grams = parse_food_text("гречка 350 ккал 150 грамм")
    assert name == "гречка"
    assert cal == 350
    assert grams == 150

def test_parse_name_only():
    name, cal, grams = parse_food_text("молоко")
    assert name == "молоко"
    assert cal is None
    assert grams is None

def test_parse_no_units():
    name, cal, grams = parse_food_text("чай")
    assert name == "чай"

def test_parse_decimal():
    name, cal, grams = parse_food_text("творог 121,5 калорий на 100 грамм")
    assert cal == 121.5
    assert grams == 100
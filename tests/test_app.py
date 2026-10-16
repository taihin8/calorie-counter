import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_imports():
    """Проверяем, что модули импортируются"""
    from app import app
    assert app is not None

def test_config():
    """Проверяем конфиг"""
    from app import app
    assert app.config['SECRET_KEY'] is not None

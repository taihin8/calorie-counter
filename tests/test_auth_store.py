import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import services.auth_store as store
import tempfile
import pytest


@pytest.fixture(autouse=True)
def tmp_store():
    tmp = tempfile.mkdtemp()
    store.STORE_PATH = os.path.join(tmp, 'known_users.json')
    yield


def test_empty():
    assert store.get_last_user() is None
    assert store.get_known_users() == []


def test_save_last_user_order():
    store.save_last_user('alice')
    store.save_last_user('bob')
    store.save_last_user('alice')  # alice снова — должна стать первой
    assert store.get_known_users() == ['alice', 'bob']
    assert store.get_last_user() == 'alice'


def test_clear_last_user_keeps_users():
    store.save_last_user('alice')
    store.clear_last_user()
    assert store.get_last_user() is None
    assert store.get_known_users() == ['alice']
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from services.updater import parse_version, check_for_update
from unittest.mock import patch


def test_parse_version():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("2.0.0") == (2, 0, 0)
    assert parse_version("not-a-version") is None


def test_check_update_has_newer():
    fake = {"tag_name": "v99.0.0", "assets": [{"name": "app.apk",
            "browser_download_url": "https://x/app.apk"}]}
    with patch("urllib.request.urlopen") as mock:
        mock.return_value.__enter__.return_value.read.return_value = json_dumps(fake)
        r = check_for_update("user/repo")
    assert r["has_update"] is True
    assert r["latest"] == "v99.0.0"
    assert r["download_url"] == "https://x/app.apk"


def test_check_update_no_apk_asset():
    fake = {"tag_name": "v1.0.0", "assets": []}
    with patch("urllib.request.urlopen") as mock:
        mock.return_value.__enter__.return_value.read.return_value = json_dumps(fake)
        r = check_for_update("user/repo")
    assert r["has_update"] is False
    assert r["download_url"] is None


def test_check_update_error():
    with patch("urllib.request.urlopen", side_effect=Exception("no internet")):
        r = check_for_update("user/repo")
    assert r["error"] is not None
    assert r["has_update"] is False


def json_dumps(d):
    import json
    return json.dumps(d).encode()
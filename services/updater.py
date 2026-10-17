"""Проверка новой версии через GitHub Releases."""
import urllib.request
import json
import os
from services.version import VERSION, GITHUB_REPO


def download_apk(url, dest_path, on_progress=None, chunk=64 * 1024):
    """Скачивает APK потоком, вызывая on_progress(скачано, всего_байт).
    Возвращает число скачанных байт. Всего может быть 0 (нет Content-Length).
    """
    req = urllib.request.Request(url, headers={"User-Agent": "calorie-counter"})
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
        try:
            total = int(resp.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            total = 0
        done = 0
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            f.write(buf)
            done += len(buf)
            if on_progress:
                on_progress(done, total)
    return done


def parse_version(tag):
    """'v1.2.3' -> (1, 2, 3). Нестандартные теги -> None."""
    t = tag.lstrip('vV')
    parts = t.split('.')
    try:
        nums = tuple(int(p) for p in parts[:3])
    except ValueError:
        return None
    return nums if len(nums) == 3 else None


def _local_version_tuple():
    parts = VERSION.split('.')
    return tuple(int(p) for p in parts)


def check_for_update(repo=None):
    """Запрашивает последний релиз. Возвращает dict:
    {'has_update': bool, 'latest': str|None, 'download_url': str|None,
     'error': str|None}
    """
    repo = repo or GITHUB_REPO
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "calorie-counter"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        latest_tag = data.get("tag_name", "")
        latest_tuple = parse_version(latest_tag)
        if latest_tuple is None:
            return {"has_update": False, "latest": None, "download_url": None, "error": None}

        # ищем APK среди ассетов релиза
        apk_url = None
        for asset in data.get("assets", []):
            if asset["name"].endswith(".apk"):
                apk_url = asset["browser_download_url"]
                break

        has_update = _local_version_tuple() < latest_tuple
        return {"has_update": has_update, "latest": latest_tag,
                "download_url": apk_url, "error": None}
    except Exception as e:
        return {"has_update": False, "latest": None, "download_url": None,
                "error": str(e)}
"""Патч flet_audio на канал будильника: идемпотентность и корректность."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from tools.patch_flet_audio import patch_file, MARKER, ALARM_CONTEXT


def test_patch_is_idempotent(tmp_path):
    """Повторное применение ничего не меняет: сборка не зависит от числа запусков."""
    src = tmp_path / "audio.dart"
    src.write_text(
        "class AudioService extends FletService {\n"
        "  AudioPlayer player = AudioPlayer();\n"
        "\n"
        "    _onSeekCompleteSubscription = player.onSeekComplete.listen((event) {\n"
        "      control.triggerEvent(\"seek_complete\");\n"
        "    });\n"
        "\n"
        "    update();\n"
        "  }\n",
        encoding="utf-8",
    )
    assert patch_file(src) == "patched"
    once = src.read_text(encoding="utf-8")
    assert MARKER in once
    assert "usageType: AndroidUsageType.alarm" in once
    assert patch_file(src) == "already"        # второй раз — без изменений
    assert src.read_text(encoding="utf-8") == once


def test_patch_reports_error_on_unexpected_file(tmp_path):
    """Если структура файла другая, патч честно сообщает об ошибке, а не ломает."""
    src = tmp_path / "audio.dart"
    src.write_text("// не тот файл\n", encoding="utf-8")
    assert patch_file(src).startswith("error")
    assert src.read_text(encoding="utf-8") == "// не тот файл\n"

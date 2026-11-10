"""Патч Flutter-части flet_audio: играть по каналу будильника.

Зачем: flet_audio создаёт AudioPlayer() без AudioContext, поэтому звук идёт
по медиа-каналу — при выключенном или минимальном медиа-звуке будильник
не слышно. Android даёт отдельный канал будильника (USAGE_ALARM), который
не зависит от медиа-громкости и играет даже в беззвучном режиме.

Патч идемпотентный: повторный запуск ничего не меняет. Применяется к
flutter-части pip-пакета flet-audio в текущем venv перед сборкой APK.

Запуск: python tools/patch_flet_audio.py
"""
import re
import sys
from pathlib import Path

MARKER = "usageType: AndroidUsageType.alarm"

# Контекст: тип sonification, канал alarm, фокус на время звонка, экран не гаснет
ALARM_CONTEXT = """
  // Канал будильника: играет даже при выключенном/минимальном медиа-звуке
  static final AudioContext _alarmContext = AudioContext(
    android: AudioContextAndroid(
      contentType: AndroidContentType.sonification,
      usageType: AndroidUsageType.alarm,
      audioFocus: AndroidAudioFocus.gainTransient,
      stayAwake: true,
    ),
  );
"""

OLD_PLAYER = "  AudioPlayer player = AudioPlayer();"
NEW_PLAYER = """  AudioPlayer player = AudioPlayer();
""" + ALARM_CONTEXT

OLD_INIT_TAIL = """    _onSeekCompleteSubscription = player.onSeekComplete.listen((event) {
      control.triggerEvent("seek_complete");
    });

    update();
  }"""

NEW_INIT_TAIL = """    _onSeekCompleteSubscription = player.onSeekComplete.listen((event) {
      control.triggerEvent("seek_complete");
    });

    // Контекст ставим ДО первого update(): иначе источник откроется на
    // медиа-канале и будильник будет тихим.
    () async {
      try {
        await player.setAudioContext(_alarmContext);
      } catch (e) {
        // на платформах без поддержки (desktop) играем как раньше
        debugPrint("setAudioContext failed: $e");
      }
      update();
    }();
  }"""


def patch_file(path: Path) -> str:
    """Возвращает: patched | already | error."""
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return "already"
    if OLD_PLAYER not in text:
        return "error: не найдено объявление плеера"
    if OLD_INIT_TAIL not in text:
        return "error: не найден конец init()"

    text = text.replace(OLD_PLAYER, NEW_PLAYER, 1)
    text = text.replace(OLD_INIT_TAIL, NEW_INIT_TAIL, 1)
    path.write_text(text, encoding="utf-8")
    return "patched"


def _installed() -> Path:
    """Flutter-часть рядом с python-пакетом: путь не зависит от платформы."""
    try:
        import flet_audio
        return (Path(flet_audio.__file__).parent.parent
                / "flutter" / "flet_audio" / "lib" / "src" / "audio.dart")
    except Exception:
        return None


def find_targets() -> list:
    """Все копии flutter-части flet_audio, которые видит сборка."""
    root = Path(__file__).resolve().parent.parent
    targets = [
        _installed(),
        root / ".venv/Lib/site-packages/flutter/flet_audio/lib/src/audio.dart",
        root / "build/flutter-packages/flet_audio/lib/src/audio.dart",
    ]
    # один и тот же файл может найтись двумя путями — патчим по разу
    seen, unique = set(), []
    for p in targets:
        if p and p.exists() and p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def main() -> int:
    targets = find_targets()
    if not targets:
        print("не найдена flutter-часть flet_audio — сначала установите flet-audio")
        return 1
    failed = False
    for path in targets:
        result = patch_file(path)
        print(f"{result:8} {path.relative_to(Path.cwd())}")
        if result.startswith("error"):
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

import sys, os, wave, io
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.sounds import sound_bytes
from services.alarm_service import SOUNDS


def test_every_sound_is_valid_wav():
    """Каждый встроенный звук отдаётся корректным WAV и не пустой."""
    for sid in range(len(SOUNDS)):
        data = sound_bytes(sid)
        assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
        with wave.open(io.BytesIO(data)) as w:
            assert w.getnchannels() == 1
            assert w.getnframes() > 0


def test_sounds_are_distinct_and_cached():
    a, b = sound_bytes(0), sound_bytes(1)
    assert a != b                       # треки не одинаковые
    assert sound_bytes(0) is a          # второй вызов — из кэша

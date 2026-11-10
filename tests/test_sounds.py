import sys, os, wave, io, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.sounds import sound_bytes, RATE, SECONDS, PEAK
from services.alarm_service import SOUNDS


def _samples(sid):
    with wave.open(io.BytesIO(sound_bytes(sid))) as w:
        frames = w.readframes(w.getnframes())
    return struct.unpack(f"<{len(frames)//2}h", frames)


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


def test_sounds_are_smooth():
    """Мелодии плавные: без резких скачков (щелчков) между сэмплами."""
    for sid in range(len(SOUNDS)):
        s = _samples(sid)
        peak = max(abs(v) for v in s)
        # скачок больше 25% от пика слышен как щелчок
        clicks = sum(1 for i in range(len(s) - 1)
                     if abs(s[i + 1] - s[i]) > peak * 0.25)
        assert clicks == 0, f"звук {sid}: {clicks} резких скачков"


def test_loop_seam_is_quiet():
    """Стык петли не щёлкает: разрыв между концом и началом мал."""
    for sid in range(len(SOUNDS)):
        s = _samples(sid)
        peak = max(abs(v) for v in s)
        assert abs(s[0] - s[-1]) < peak * 0.05, f"звук {sid}: слышимый стык"


def test_sound_is_long_enough_for_loop():
    """Трек достаточно длинный, чтобы петля не была навязчивой."""
    assert SECONDS >= 8
    for sid in range(len(SOUNDS)):
        with wave.open(io.BytesIO(sound_bytes(sid))) as w:
            assert w.getframerate() == RATE
            assert w.getnframes() >= RATE * 8

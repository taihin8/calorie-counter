"""Встроенные звуки будильника.

Треки синтезируются в памяти (без файлов в репозитории) и отдаются плееру
как WAV-байты: сервис звука принимает src=bytes.
"""
import array
import io
import math
import random
import wave

RATE = 22050          # хватает для шума-подложки, файл выходит ~0.26 МБ за 6 с
SECONDS = 6
_cache = {}


def _lowpass(samples, alpha):
    """Однополюсный ФНЧ: alpha меньше — глуше и «дальше»."""
    out = []
    prev = 0.0
    for s in samples:
        prev += alpha * (s - prev)
        out.append(prev)
    return out


def _loop_fade(samples, fade=RATE // 8):
    """Сводит края петли в ноль, чтобы стык не щёлкал."""
    n = len(samples)
    fade = min(fade, n // 2)
    for i in range(fade):
        k = i / fade
        samples[i] *= k
        samples[n - 1 - i] *= k
    return samples


def _to_wav(samples):
    buf = io.BytesIO()
    data = array.array("h", (int(max(-1.0, min(1.0, s)) * 20000) for s in samples))
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    return buf.getvalue()


def _build(sound_id):
    """Синтез трека по id. Параметры подобраны на слух, не претендуют на реализм."""
    rng = random.Random(1000 + sound_id)
    n = RATE * SECONDS
    raw = [rng.uniform(-1.0, 1.0) for _ in range(n)]

    if sound_id == 0:      # Дождь — высокочастотный шум с частыми всплесками
        s = _lowpass(raw, 0.55)
        s = [v * (0.7 + 0.3 * math.sin(2 * math.pi * 0.7 * i / RATE)) for i, v in enumerate(s)]
    elif sound_id == 1:    # Ручей — журчание: шум с медленной модуляцией
        s = _lowpass(raw, 0.18)
        s = [v * (0.6 + 0.4 * math.sin(2 * math.pi * 0.35 * i / RATE)) for i, v in enumerate(s)]
    elif sound_id == 2:    # Лес — глухой фон и редкие «птицы»
        s = _lowpass(raw, 0.08)
        for _ in range(12):
            start = rng.randrange(0, max(1, n - RATE // 4))
            for k in range(RATE // 4):
                s[start + k] += 0.35 * math.sin(2 * math.pi * 2400 * k / RATE) * (1 - k / (RATE // 4))
    elif sound_id == 3:    # Озеро — низкий гул с медленными волнами
        s = _lowpass(raw, 0.04)
        s = [v * (0.5 + 0.5 * math.sin(2 * math.pi * 0.12 * i / RATE)) for i, v in enumerate(s)]
    else:                  # Ветер — очень низкий шум с набегами
        s = _lowpass(raw, 0.02)
        s = [v * (0.4 + 0.6 * abs(math.sin(2 * math.pi * 0.09 * i / RATE))) for i, v in enumerate(s)]

    # нормировка по пику, чтобы звуки не отличались громкостью
    peak = max(1e-9, max(abs(v) for v in s))
    s = [v / peak * 0.9 for v in s]
    return _to_wav(_loop_fade(s))


def sound_bytes(sound_id):
    """WAV-байты встроенного трека (кэшируются после первого синтеза)."""
    if sound_id not in _cache:
        _cache[sound_id] = _build(sound_id)
    return _cache[sound_id]

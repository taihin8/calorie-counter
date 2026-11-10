"""Встроенные звуки будильника.

Треки синтезируются в памяти (файлов в репозитории нет) и отдаются плееру
как WAV-байты. Мелодии плавные: только синусоиды и мягко отфильтрованный шум,
без щелчков и резких всплесков. Край петли сшивается кроссфейдом, поэтому
повтор не «стучит».
"""
import array
import io
import math
import random
import wave

RATE = 22050          # хватает для фоновых тембров; 10 с ≈ 0.4 МБ на трек
SECONDS = 10          # длиннее трек — петля незаметнее
PEAK = 0.85           # запас до клиппинга при суммировании
_cache = {}


def _lowpass(samples, cutoff):
    """Однополюсный ФНЧ; мягче и без «песка», чем резкий срез."""
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / RATE)
    out = []
    prev = 0.0
    for s in samples:
        prev += alpha * (s - prev)
        out.append(prev)
    return out


def _tone(freq, n, amp=1.0, vib_hz=0.0, vib_depth=0.0):
    """Синус с необязательной медленной вибрацией частоты."""
    out = []
    phase = 0.0
    for i in range(n):
        f = freq * (1.0 + vib_depth * math.sin(2 * math.pi * vib_hz * i / RATE))
        phase += 2 * math.pi * f / RATE
        out.append(amp * math.sin(phase))
    return out


def _drift(n, amp, hz, base):
    """Медленное изменение громкости: base ± amp."""
    return [base + amp * math.sin(2 * math.pi * hz * i / RATE) for i in range(n)]


def _add(dst, src, gain=1.0):
    for i in range(len(dst)):
        dst[i] += src[i] * gain


def _mul(dst, env):
    for i in range(len(dst)):
        dst[i] *= env[i]


def _seamless(samples, fade):
    """Сшивает петлю: хвост вплавляется в начало, стык без щелчка."""
    n = len(samples)
    fade = min(fade, n // 3)
    out = samples[:n - fade]
    for i in range(fade):
        k = i / fade
        out[i] = samples[i] * k + samples[n - fade + i] * (1.0 - k)
    return out


def _build(sound_id):
    """Синтез одного трека. Тембры подобраны на слух, реализма не обещают."""
    rng = random.Random(2000 + sound_id)
    n = RATE * SECONDS
    out = [0.0] * n

    if sound_id == 0:      # Дождь — ровный мягкий шум с лёгким дыханием
        noise = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        # три прохода ФНЧ: высокие «искры» уходят, остаётся шелест
        bed = _lowpass(_lowpass(_lowpass(noise, 700), 700), 700)
        _add(out, bed, 1.0)
        _mul(out, _drift(n, 0.12, 0.15, 0.88))

    elif sound_id == 1:    # Ручей — журчание: шум + мягкие тона с вибрацией
        noise = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        _add(out, _lowpass(_lowpass(noise, 700), 700), 0.55)
        _add(out, _tone(220, n, 0.16, vib_hz=0.4, vib_depth=0.02))
        _add(out, _tone(330, n, 0.10, vib_hz=0.5, vib_depth=0.02))
        _mul(out, _drift(n, 0.10, 0.25, 0.90))

    elif sound_id == 2:    # Лес — тихий аккорд и редкие мягкие «птицы»
        _add(out, _tone(196, n, 0.30, vib_hz=0.1, vib_depth=0.004))
        _add(out, _tone(294, n, 0.20, vib_hz=0.13, vib_depth=0.004))
        _add(out, _tone(392, n, 0.12, vib_hz=0.17, vib_depth=0.004))
        _mul(out, _drift(n, 0.10, 0.08, 0.90))
        # птицы: короткие посвисты с плавными фронтами, без щелчков
        for _ in range(5):
            length = RATE // 3
            start = rng.randrange(0, max(1, n - length))
            f0 = rng.uniform(1700.0, 2300.0)
            for k in range(length):
                # приподнятый косинус: мягкая атака и мягкий спад
                env = 0.5 - 0.5 * math.cos(2 * math.pi * k / length)
                freq = f0 * (1.0 + 0.18 * k / length)
                out[start + k] += 0.12 * env * math.sin(2 * math.pi * freq * k / RATE)

    elif sound_id == 3:    # Озеро — низкий гул с медленными волнами
        _add(out, _tone(110, n, 0.40, vib_hz=0.05, vib_depth=0.01))
        _add(out, _tone(165, n, 0.22, vib_hz=0.06, vib_depth=0.01))
        _add(out, _lowpass([rng.uniform(-1.0, 1.0) for _ in range(n)], 300), 0.30)
        _mul(out, _drift(n, 0.18, 0.10, 0.82))

    else:                  # Ветер — очень мягкий низкий шум с набегами
        noise = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        _add(out, _lowpass(_lowpass(noise, 400), 400), 1.0)
        _mul(out, _drift(n, 0.30, 0.07, 0.70))

    # нормировка: треки не должны отличаться громкостью
    peak = max(1e-9, max(abs(v) for v in out))
    out = [v / peak * PEAK for v in out]
    # сшивка петли: 2 с — длиннее стык, незаметнее повтор
    return _to_wav(_seamless(out, RATE * 2))


def _to_wav(samples):
    buf = io.BytesIO()
    data = array.array("h", (int(max(-1.0, min(1.0, s)) * 32000) for s in samples))
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    return buf.getvalue()


def sound_bytes(sound_id):
    """WAV-байты встроенного трека (кэшируются после первого синтеза)."""
    if sound_id not in _cache:
        _cache[sound_id] = _build(sound_id)
    return _cache[sound_id]

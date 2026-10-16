"""Распознавание речи через микрофон. Запускается в фоне, результат — в колбэк."""
import re

def recognize_async(run_in_thread, on_result, on_start=None):
    """Слушает микрофон и вызывает on_result(текст) в потоке Flet.

    run_in_thread — page.run_thread, чтобы обновлять UI.
    on_result    — функция(текст), вызывается после распознавания.
    on_start     — необязательный колбэк, вызывается когда запись началась.
    """
    import threading
    import speech_recognition as sr

    if on_start:
        run_in_thread(on_start)

    def listen():
        r = sr.Recognizer()
        text = ""
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5, phrase_time_limit=15)
            text = r.recognize_google(audio, language="ru-RU")
        except Exception:
            text = ""
        run_in_thread(lambda: on_result(text))

    threading.Thread(target=listen, daemon=True).start()

def parse_food_text(text):
    """Разбирает голосовую фразу продукта: 'яблоко 52 калории на 200 грамм'.

    Возвращает (название, калории, граммы) или (название, None, None).
    """
    parts = text.split()
    calories = None
    grams = None
    name_parts = []

    for i, w in enumerate(parts):
        wl = w.lower()
        if wl in ('на', 'по', 'в', 'около', 'примерно', 'это', 'там'):
            continue
        if 'кал' in wl:
            m = re.search(r'\d+[.,]?\d*', w)
            if not m and i > 0:
                m = re.search(r'\d+[.,]?\d*', parts[i - 1])
            if m:
                calories = float(m.group().replace(',', '.'))
            continue
        if 'грамм' in wl or wl == 'гр' or wl == 'г':
            m = re.search(r'\d+[.,]?\d*', w)
            if not m and i > 0:
                m = re.search(r'\d+[.,]?\d*', parts[i - 1])
            if m:
                grams = float(m.group().replace(',', '.'))
            continue
        if re.fullmatch(r'\d+[.,]?\d*', w):
            # число без единицы: если калории ещё нет — это калории, иначе граммы
            continue
        name_parts.append(w)

    name = " ".join(name_parts).strip() or text.strip()
    return name, calories, grams
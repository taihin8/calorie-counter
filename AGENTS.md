# Специфика проекта Daily_Journal

Общие правила — в `~/.dsh/AGENTS.md` (загружаются автоматически).

## Сборка APK и релиз

Сборка APK и релиз — [BUILD.md](BUILD.md) (по ссылке, при сборке).

## Веб-режим

Запускать веб только с `CALORIE_MODE=web` (иначе мьютекс блокирует десктоп):

```powershell
$env:CALORIE_MODE="web"
& ".\.venv\Scripts\python.exe" -u ".\.venv\Scripts\flet.exe" run --web main.py --port 8001
```

Без этой переменной веб держит мьютекс, и десктоп-копия при запуске молча завершается (exit 0, окно не появляется).

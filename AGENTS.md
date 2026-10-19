# Правила работы

Единый файл правил проекта — читай и соблюдай. Все правила и полный текст Ponytail — здесь.
Логи и диагностика DSH — [logs/LOGGING.md](logs/LOGGING.md) (по ссылке, когда нужны).
Сборка APK и релиз — [BUILD.md](BUILD.md) (по ссылке, при сборке).

## 📋 Общие правила

1. **Краткость** — отвечай по делу, без лишних деталей. Нужно подробнее — я спрошу.
2. **Код на русском** — комментарии, README, сообщения в коде — на русском; имена переменных, функций, классов — на английском. Команды и пути — как есть.
3. **Подтверждение и «на сухую»** — спрашивай перед изменением файлов, запуском команд, git push и прочими необратимыми действиями (исключение: чтение данных). Перед применением покажи diff или список изменений и зачем они.
4. **Уточнение** — непонятно или неоднозначно → уточни, не делай наугад.
5. **Тесты** — новая или изменённая логика → напомни написать тест на ключевые сценарии; порог «когда тест не нужен» — в разделе Ponytail ниже.
6. **Проверка перед заливкой** — перед git push: прогнать существующие тесты, убедиться, что новые проходят, и только потом заливать.
7. **Commits** — conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`); одна задача — один коммит, не смешивать фичу, рефакторинг и багфиксы.
8. **Чистота проекта** — временные файлы, логи сборки, `.tmp` — не коммитить; лишнее — в `.gitignore`; перед коммитом проверь, что ничего лишнего не улетает.
9. **Документация** — README и AGENTS.md обновлять вместе с кодом, чтобы не расходились.
10. **Секреты — не в код** — ключи, токены, пароли, `.env` — никогда не коммитить (в `.gitignore`); учётные данные DSH — в `~/.dsh/.credentials.yaml`. Токен литералом в команде = утечка в логи сессий: бери из переменной окружения.
11. **Бэкап перед опасным** — массовая замена, удаление файлов, рефакторинг → сначала свежий коммит; иначе убедись, что изменения обратимы.
12. **Новая модель в конфиге** — при добавлении модели в `cordis.patch.yml` проверять `input: [text, image]` для зрячих и корректные `contextWindow`/`maxTokens`.
13. **Веб-режим** — запускать только с `CALORIE_MODE=web` (иначе мьютекс блокирует десктоп); полная команда — в BUILD.md.
14. **Обратная связь** — просят опасное или неправильное → скажи об этом.
15. **Новая сессия при 80%+** — индикатор контекста в футере ≥80% → напомни о новой сессии.
16. **Конкретные файлы** — при обращении к коду указывай конкретные файлы (`@путь/к/файлу`), а не целые папки.
17. **Ponytail (ленивый сеньор)** — применяется постоянно; соблюдай раздел Ponytail в конце этого файла.

## 🎤 Голосовой ввод

- Микрофон в DSH Web — через Tampermonkey (`dsh-voice-input.user.js`)
- Непрерывный режим: 🎤 → говорить → ⏹
- Текст вставляется через `execCommand('insertText')`

## 🐙 Git

- Git: `C:\Program Files\Git\cmd\git.exe` (v2.55.0)
- Запускать git только с полным доступом (`danger-full-access`) — иначе песочница DSH блокирует

## 🖥️ DSH

- Запуск: `start-dsh.bat` (или `dsh-silent.vbs`)
- Новый плагин → перезапустить DSH
- Плагины профиля: `cordis.patch.yml`

## Контекст

- `$DSH_HOME` = `C:\Users\TEST\.dsh`
- Настройки моделей: `C:\Users\TEST\.dsh\profiles\web\cordis.patch.yml`

---

## 🐴 Ponytail: режим «ленивого сеньора» (постоянно)

Правила из https://github.com/DietrichGebert/ponytail — применять постоянно при любой работе с кодом.

You are a lazy senior developer. The best code is the code never written. You solve the whole problem with the least new code. End your reply with one or two lines: what you skipped or did not check, and any risk the user must know.

### Before you write

Read the task and the code it touches. List every place your change must reach: callers, tests, fixtures, config, exports. Check what your change could break for users: data it would destroy or expose, callers that stop working. That is scope. Extra features are not.

### The smallest complete change

Take the first option that fully works:

1. Does it need to exist? Skip features, options and flexibility nobody asked for, and name them in one line. A vague request ("build me X") gets the smallest version that does the core job.
2. Already in this codebase (a helper, component, service, pattern)? Use it the way the surrounding code does.
3. Standard library or a platform feature? Use it, unless the project has its own. A house component beats a native widget.
4. An installed dependency? Use it. Never add a dependency for a few lines.
5. Can it be one line a reader gets at a glance? One line.
6. Otherwise: the minimum code that works.

- Be lazy about the solution, never about the change itself: finish every part the task needs, including the callers, tests and fixtures your change breaks.
- No abstraction, wrapper, type conversion, option, config, boilerplate or "for later" code nobody asked for. Keep values in the form the platform already gives you. Deletion beats addition. Keep the structure the codebase already has: its layers, interfaces and conventions.
- The shortest working diff wins, once you know everything it must touch. A one-liner that needs decoding is not short.
- Comment only the why the code cannot show, in one line.
- Bug fix: before you edit, grep every caller of the function you touch, then fix the root cause once in the shared code.
- Code you move or merge keeps its error handling and validation.
- Between options of equal size, take the one that is correct on edge cases.
- Lazy code without its check is unfinished: new non-trivial logic (a branch, a loop, a parser, money or security, or a whole new script or app) leaves one small test or an assert-based self-check. Trivial changes need none.
- A shortcut with a known limit gets a code comment in this form: `shortcut: <the limit>, <when to upgrade>`.

Never cut: validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs, anything the user asked for.
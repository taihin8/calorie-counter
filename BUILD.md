# Сборка APK и релиз

## Команда сборки

```powershell
$env:JAVA_HOME="C:\jdk17"; $env:ANDROID_HOME="C:\Android\sdk"; $env:ANDROID_SDK_ROOT="C:\Android\sdk"
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; $env:FLET_CLI_SKIP_FLUTTER_DOCTOR="1"
$env:PATH="C:\jdk17\bin;C:\Android\sdk\cmdline-tools\latest\bin;C:\Android\sdk\platform-tools;C:\flutter\bin;$env:PATH"
cd "C:\Users\TEST\OpenideProjects\Daily_Journal"
& ".\.venv\Scripts\flet.exe" build apk `
  --project "calorie-counter" `
  --product "Calorie Counter" `
  --org "com.taihin8" `
  --company "Calorie Counter" `
  --build-version "X.Y.Z" `
  --android-permissions "android.permission.REQUEST_INSTALL_PACKAGES=true" `
  --clear-cache `
  --yes
```

`REQUEST_INSTALL_PACKAGES` — без неё Android 8+ молча блокирует установку APK
из приложения (кнопка «Установить» в системном инсталляторе не работает).

## Обязательная проверка пакета (после КАЖДОЙ сборки)

```powershell
& "C:\Android\sdk\build-tools\35.0.0\aapt.exe" dump badging <путь к apk>
```

Должно быть ровно:
- `package: name='com.taihin8.calorie_counter'`
- `application-label:'Calorie Counter'`

Иначе APK встанет ВТОРЫМ приложением (пакет `daily_journal`) и пользователь потеряет данные.

## Известные грабли

- Флаг версии — `--build-version`, НЕ `--build-name` (тот даст ошибку unrecognized arguments).
- `--project Daily_Journal` → пакет `com.taihin8.daily_journal` — НЕ использовать. Slug: `calorie-counter` → `calorie_counter`.
- `copy_build_output` часто падает `PermissionError [WinError 32]` (build\apk занят) — тогда вручную:
  `Copy-Item build\flutter\build\app\outputs\flutter-apk\app-release.apk build\apk\calorie-counter-<ver>.apk -Force`
- Сборка долгая (~2–3 мин прогретого Gradle) — запускать фоновым джобом.

## Проверка APK в эмуляторе (без телефона)

AVD `nova13`: 1224×2700, 440 dpi, Android 15 без Google Play (как Huawei nova 13).

```powershell
.\test_apk.bat                     # возьмёт build\apk\calorie-counter.apk
.\test_apk.bat путь\к\app.apk
```

Скрипт поднимает эмулятор, ставит APK (`adb install -r -g`) и запускает приложение.

Грабли:
- Без `-feature -Wifi,-BluetoothEmulation,-VirtioWifi` загрузка виснет: падает `netsimd.exe`, adb навсегда показывает `offline`.
- Ускоритель — AEHD (`C:\Android\sdk\extras\google\Android_Emulator_Hypervisor_Driver`); старая служба HAXM остановлена — конфликтует.
- Модель не подменяется: `ro.product.model` остаётся `Android SDK built for x86_64`.

Замеры: установка APK 2,5 с, холодный старт 50 с, из снапшота 30 с.

## Сборка, когда Flutter/AppData вне рабочей папки (песочница DSH)

Если сборка запускается из-под DSH, дочерние процессы Python не могут писать
вне рабочей папки: `flet build apk` зависает на «Initializing apk build...»,
потому что `flutter.BAT` не открывает `C:\flutter\bin\cache\lockfile`.

Рабочий обход — собирать скриптом, где всё нужное лежит внутри проекта:

1. Скопировать Flutter в `.tmp\flutter` и pub-кэш в `.tmp\pub` (один раз).
2. В скрипте задать окружение:
   - `FLUTTER_ROOT`, `PUB_CACHE`, `GRADLE_USER_HOME` — внутрь `.tmp\`;
   - `APPDATA`, `LOCALAPPDATA`, `USERPROFILE`, `HOME`, `TEMP`, `TMP` — внутрь `.tmp\`;
   - `FLET_CACHE_DIR=C:\Users\<user>\.flet\cache` — там уже лежат
     `python-android-dart-*.tar.gz`, иначе Gradle идёт в github и падает по таймауту;
   - `JAVA_TOOL_OPTIONS=-Duser.home=<проект>\.tmp\home` и копия
     `debug.keystore` в `.tmp\home\.android\` — иначе `validateSigningRelease`
     не может создать `.lock` рядом с ключом;
   - `--exclude .tmp` в `flet build` — иначе упаковщик копирует сам себя.
3. Отключить скачивание дистрибутива Python, если сеть нестабильна: положить
   в `GRADLE_USER_HOME/init.d/` скрипт, выключающий задачи `downloadDistArchive_*`.

Важно: перед повторной сборкой убить Gradle-демоны (`Stop-Process java`), иначе
они переиспользуют старое окружение и падают на keystore.

Место: копия Flutter (~1.5 ГБ) + Gradle-кэш (~4.5 ГБ) + сборка. При нехватке
диска `pip` падает с `[Errno 28] No space left on device`.

## Тесты перед сборкой

```powershell
& ".\.venv\Scripts\python.exe" -m py_compile screens\diary.py services\updater.py services\version.py
& ".\.venv\Scripts\python.exe" -m pytest tests\ -q
```

## Релиз на GitHub

APK > 100 МБ — ТОЛЬКО через API релизов, не через git (`.gitignore` исключает build/ и *.apk):

1. Токен — только из переменной окружения `$env:GH_TOKEN` (литерал в команде = утечка в логи).
2. Удалить старый ассет:
   `DELETE /repos/taihin8/calorie-counter/releases/assets/<asset_id>` → ждать HTTP 204.
3. Загрузить новый:
   `POST https://uploads.github.com/repos/taihin8/calorie-counter/releases/<release_id>/assets?name=calorie-counter-<ver>.apk`
   curl: `-H "Authorization: token $env:GH_TOKEN" -H "Content-Type: application/octet-stream" --data-binary "@<apk>"` → ждать HTTP 201, сверить `digest` с локальным SHA256.
4. Кириллицу в JSON (название релиза) писать файлом через Python `json.dump(..., ensure_ascii=False)` — PowerShell `ConvertTo-Json` портит кириллицу («400 Problems parsing JSON»).

## Веб-режим

Запускать ТОЛЬКО с `CALORIE_MODE=web`:

```powershell
$env:CALORIE_MODE="web"
& ".\.venv\Scripts\python.exe" -u ".\.venv\Scripts\flet.exe" run --web main.py --port 8001
```

Без этой переменной веб держит мьютекс, и десктоп-копия при запуске молча завершается (exit 0, окно не появляется).
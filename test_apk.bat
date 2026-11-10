@echo off
chcp 65001 >nul
rem Проверка APK в эмуляторе Huawei nova 13 (без телефона)
rem Использование: test_apk.bat [путь\к\app.apk]
setlocal
set "SDK=C:\Android\sdk"
set "PATH=%SDK%\platform-tools;%SDK%\emulator;%PATH%"
set "APK=%~1"
if "%APK%"=="" set "APK=%~dp0build\apk\calorie-counter.apk"
if not exist "%APK%" (echo Нет файла: %APK% & exit /b 1)

rem 1. эмулятор уже запущен? иначе стартуем (Wifi/BLE-эмуляция ломает boot на этом ПК)
adb devices | findstr "device" | findstr "emulator" >nul || (
  echo Запускаю эмулятор nova13...
  start "" "%SDK%\emulator\emulator.exe" -avd nova13 ^
    -feature -Wifi,-BluetoothEmulation,-VirtioWifi -no-audio -gpu swiftshader_indirect
  adb wait-for-device
)

rem 2. ждём полной загрузки Android
:waitboot
set "BOOT="
for /f "delims=" %%b in ('adb shell getprop sys.boot_completed 2^>nul') do set "BOOT=%%b"
if not "%BOOT%"=="1" ( timeout /t 3 >nul & goto waitboot )

rem 3. ставим APK и запускаем главную активность
adb logcat -c
adb install -r -g "%APK%" || (echo Ошибка установки & exit /b 1)

set "PKG="
for /f "tokens=2 delims='" %%i in ('"%SDK%\build-tools\35.0.0\aapt.exe" dump badging "%APK%" ^| findstr /b "package: name"') do set "PKG=%%i"
if "%PKG%"=="" (echo Не удалось определить пакет & exit /b 1)

echo Запускаю %PKG% ...
adb shell monkey -p %PKG% -c android.intent.category.LAUNCHER 1 >nul 2>&1
echo Готово. Окно эмулятора на экране; логи: adb logcat
endlocal

@echo off
chcp 65001 >nul
echo ===== Установка Flutter SDK =====
if not exist "C:\flutter\bin\flutter.bat" (
    echo Клонирую Flutter (стабильная ветка)...
    git clone --depth 1 --branch stable https://github.com/flutter/flutter.git C:\flutter
) else (
    echo Flutter уже есть
)
set PATH=C:\flutter\bin;%PATH%
echo Flutter: & flutter --version
echo ===== Установка Android SDK =====
flutter config --disable-analytics
flutter config --android-accept-licenses
echo ===== Готово =====
echo Теперь запустите build_apk.bat для сборки APK
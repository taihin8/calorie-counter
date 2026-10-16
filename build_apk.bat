@echo off
chcp 65001 >nul
set PATH=C:\flutter\bin;%PATH%
cd /d "%~dp0"

echo ===== Сборка APK =====
echo Убедитесь, что сначала запущен setup_android.bat

flutter config --android-accept-licenses 2>nul
call .venv\Scripts\activate.bat
pip install flet 2>nul

flet build apk ^
    --project "calorie-counter" ^
    --product "Calorie Counter" ^
    --org "com.example" ^
    --company "Calorie Counter" ^
    --build-name "%APPVEYOR_BUILD_VERSION%"

echo ===== Готово! APK в build/apk/ =====
pause
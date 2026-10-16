@echo off
chcp 65001 >nul
title DSH — Проверка логов

echo ===== DSH LOG CHECKER =====
echo.

if exist "%USERPROFILE%\dsh-log.txt" (
    echo --- dsh-log.txt (последние 10 строк) ---
    powershell -Command "Get-Content '%USERPROFILE%\dsh-log.txt' -Tail 10"
) else (
    echo [dsh-log.txt не найден — DSH не запущен?]
)
echo.

echo --- Свежие сессии с ошибками ---
powershell -Command "
$dir = '$env:USERPROFILE\.dsh\storages\session_projcache\sessions'
if (Test-Path $dir) {
    Get-ChildItem $dir -Filter *.json | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object {
        Write-Host ('  [{0}] {1}' -f $_.LastWriteTime.ToString('HH:mm:ss'), $_.Name)
        $content = Get-Content $_.FullName -Raw
        if ($content -match '(?s)"stopReason"\s*:\s*"([^"]+)"') {
            Write-Host ('    stopReason: ' + $matches[1])
        }
        if ($content -match '"provider"\s*:\s*"([^"]+)"') {
            Write-Host ('    provider: ' + $matches[1])
        }
        Write-Host ''
    }
} else {
    Write-Host '  [Нет кеша сессий]'
}
"

echo.
echo === Проверка завершена ===
pause
# Логирование DSH

Здесь собрана информация о том, где искать логи, как проверять ошибки и что делать при сбоях.

---

## 📁 Где лежат логи

| Что | Путь |
|---|---|
| **Консоль DSH сервера** | `%USERPROFILE%\dsh-log.txt` |
| **Лог запуска** | `%USERPROFILE%\.dsh\logs\startup-*.log` |
| **Сессии (сжатые)** | `%USERPROFILE%\.dsh\sessions\--C-Users-TEST-projects-my-project--\*.jsonl.zstd` |
| **Кеш сессий (читаемый)** | `%USERPROFILE%\.dsh\storages\session_projcache\sessions\*.json` |
| **Учётные данные** | `%USERPROFILE%\.dsh\.credentials.yaml` |
| **Конфиг профиля** | `%USERPROFILE%\.dsh\profiles\web\cordis.patch.yml` |

## 🔍 Быстрая проверка ошибок

**Через `check-logs.bat`** — запустить в этой папке:

```bat
check-logs.bat
```

Покажет последние ошибки из `dsh-log.txt` и свежие сессионные логи.

**Через PowerShell** — вручную:

```powershell
# Ошибки сервера
Get-Content "$env:USERPROFILE\dsh-log.txt"

# Свежие сессии-кеш (ошибки, стоп-ризоны, провайдеры)
Get-ChildItem "$env:USERPROFILE\.dsh\storages\session_projcache\sessions" -Filter *.json |
  Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object {
    $_.FullName
}
```

**Через `dsh-session-scan.mjs`** — детальный разбор сжатых логов сессий:

```bash
node dsh-session-scan.mjs <путь к .jsonl.zstd> "error|fail|credential|401|400"
```

## 🐛 Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| `401 Invalid API key` | Неверный ключ провайдера | Проверить `~/.dsh/.credentials.yaml` |
| `400 context length > max` | Превышение контекста модели | Переключить на модель с большим контекстом (`gemini-3.7-flash`) или начать новую сессию |
| `MODEL_DOES_NOT_SUPPORT_IMAGES` | Модель не поддерживает картинки | Сменить модель на зрячую, или дать путь к файлу |
| `no credential for provider` | Не задан API-ключ | Сохранить ключ через ⚙️ → Models |
| `failed to import` (плагин) | Плагин не загрузился | Проверить совместимость, перезапустить DSH |

## 🔄 Что делать при сбое

1. Проверить `dsh-log.txt` на явные ошибки
2. Проверить, запущен ли DSH (`http://127.0.0.1:3080/`)
3. Если DSH упал — запустить `start-dsh.bat`
4. Если контекст переполнен — переключить модель на `gemini-3.7-flash`
5. Если ошибка persist — глянуть свежий кеш сессии через `dsh-session-scan.mjs`

---

*Последнее обновление: 28.09.2026*
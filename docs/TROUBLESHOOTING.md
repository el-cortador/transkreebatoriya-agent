# Troubleshooting — local-web runtime

Типовые сбои и их диагностика. Сначала прогоните
`scripts/verify_install.ps1` (или `.sh`) — большинство проблем видны там.

## 1. `ffmpeg не найден`

**Симптом:** задача падает с `ConversionError`, в логе «ffmpeg не найден».
**Причины:** ffmpeg не установлен или не в `PATH`.
**Решение:** установить ffmpeg и добавить в `PATH`, либо задать полный путь
в `FFMPEG_PATH` (`.env`). Проверка: `ffmpeg -version`.

## 2. `LLM-сервис постобработки недоступен`

**Симптом:** задачи с постобработкой завершаются `status=error`.

**При `LLM_PROVIDER=ollama`:** Ollama не запущена или слушает другой
хост/порт. Решение: `ollama serve`; проверить `OLLAMA_API_URL` в `.env`.
Диагностика: `curl http://localhost:11434/api/version`.

**При `LLM_PROVIDER=openrouter`:** нет интернета или недоступен OpenRouter.
Диагностика: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $OPENROUTER_API_KEY"`.

### Ошибки OpenRouter по HTTP-кодам

| Код | Причина | Решение |
|-----|---------|---------|
| 401 | Неверный/отсутствующий ключ | Проверить `OPENROUTER_API_KEY` (openrouter.ai/keys) |
| 402 | Недостаточно кредитов | Пополнить баланс OpenRouter |
| 404 | Модель не найдена | Проверить slug в `OPENROUTER_MODEL` (напр. `deepseek/deepseek-v4-pro`) |
| 429 | Rate limit | Уменьшить `POSTPROCESS_CONCURRENCY`, повторить позже |

## 3. Модель Ollama не скачана

**Симптом:** постобработка падает с ошибкой модели (HTTP 404 от Ollama).
**Решение:** `ollama pull <OLLAMA_MODEL>` (install-скрипт делает это сам).
Проверка: `ollama list`.

## 4. `Превышено время постобработки текста`

**Симптом:** `OllamaTimeoutError` на длинных файлах.
**Причины:** слабый CPU + тяжёлая модель + большой `num_ctx`.
**Решение:** увеличить `OLLAMA_TIMEOUT`; уменьшить модель
(`qwen2.5:1.5b` вместо `qwen3:4b`); уменьшить `POSTPROCESS_CHUNK_CHARS`.

## 5. Транскрибация очень медленная

**Причины/решения:** модель whisper слишком велика для CPU — поставить
`WHISPER_MODEL_NAME=tiny`; нет GPU — это нормально, ориентир для `base`
на i5-1135G7: ~1–2 минуты на минуту аудио; проверить, что не включён
лишний параллелизм (`POSTPROCESS_CONCURRENCY=1`).

## 6. CUDA: ошибки инициализации / OOM

**Симптом:** падение при загрузке модели с `WHISPER_DEVICE=auto/cuda`.
**Решение:** принудительно `WHISPER_DEVICE=cpu`; убедиться, что драйверы
и CUDA-библиотеки совместимы с установленным ctranslate2.

## 7. Результаты пропали после перезапуска

**Это ожидаемо:** состояние задач in-memory (см.
`core/contracts/pipeline_contract.md`, §4). Скачивайте `.md` сразу после
готовности. Завершённые задачи также удаляются по TTL
(`TASK_TTL_HOURS`, дефолт 24 ч).

## 8. Порт 8001 занят

**Решение:** задать `APP_PORT` в `.env` и пробросить тот же порт в
`docker-compose.yml` (`${APP_PORT:-8001}:8001`).

## 9. `Файл слишком большой` при загрузке

**Причины:** превышен `MAX_FILE_SIZE_GB` (дефолт 6). Лимит проверяется во
время потоковой записи — частично записанный файл удаляется автоматически.
**Решение:** увеличить `MAX_FILE_SIZE_GB` в `.env`.

## 10. Полезные логи и переменные

| Что | Где |
|-----|-----|
| HTTP-доступ | лог `transkreebatoriya.access` (поллинг `/api/status/` пишется не чаще раза в 3 мин на задачу) |
| Стадии пайплайна | логи `[manager]`, `[transcription]`, `[postprocess]`, `[file_handler]` |
| Отладка Ollama | `OLLAMA_DEBUG=1 ollama serve` |
| Ключевые env | `LLM_PROVIDER`, `OLLAMA_API_URL`, `OLLAMA_MODEL`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `WHISPER_MODEL_NAME`, `WHISPER_DEVICE`, `WHISPER_LANGUAGE`, `POSTPROCESS_*`, `MAX_FILE_SIZE_GB`, `TASK_TTL_HOURS` |

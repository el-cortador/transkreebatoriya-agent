# Runtime: local-web

Веб-адаптер Transkreebatoriya: FastAPI backend + браузерный UI + Docker.
Это единственный поддерживаемый runtime агента.

## Состав

| Путь | Назначение |
|------|-----------|
| `backend/` | FastAPI-приложение: API-роутеры, TaskManager, сервисы пайплайна, LLM-клиент |
| `frontend/` | Одностраничный UI (чистый HTML/CSS/JS), отдаётся backend'ом |
| `Dockerfile`, `docker-compose.yml` | Контейнерный запуск (app + ollama + ollama-init) |
| `templates/` | Шаблоны локальной конфигурации (`env.example`, Modelfile-template) |
| `install.ps1`, `install.sh` | Установка: шаблоны → локальные конфиги, проверка зависимостей, модель Ollama |
| `scripts/verify_install.*` | Проверка установки с выводом `[OK]/[WARN]/[FAIL]` |
| `start-local.ps1` | Однокомандный локальный запуск (Windows) |

## Установка

Инсталляторы **никогда не перезаписывают** существующие локальные конфиги:
если `.env` или `Modelfile.cpu-qwen25-1.5b` уже существуют, шаг
пропускается.

```powershell
# Windows
.\install.ps1

# Linux / macOS
./install.sh
```

Ручная установка: скопируйте `templates/env.example` в `.env`, далее —
`uv run uvicorn backend.main:app --port 8001`.

Docker (установка не требуется): `docker compose up --build`, подробности —
в `DOCKER.md`.

## Конфигурация

Единственный источник правды о параметрах — `templates/env.example` →
локальный `.env`. Все переменные задокументированы там и в корневом
`README.md`. Секреты (например, `HF_TOKEN`, `OPENROUTER_API_KEY`) хранятся
только в локальном `.env`, который не коммитится.

Постобработка: `LLM_PROVIDER=ollama` (локально, по умолчанию) или
`LLM_PROVIDER=openrouter` (облако; текст транскрипции уходит во внешний
API, аудио всегда остаётся локальным).

## Smoke test

1. `.\scripts\verify_install.ps1` (или `./scripts/verify_install.sh`) — все
   проверки `[OK]`.
2. Запустить сервер, открыть `http://localhost:8001` — страница загружается,
   drop-zone доступна.
3. `GET /api/config` возвращает `200` с `allowed_extensions` и
   `max_file_size_gb`.
4. Загрузить короткий аудиофайл (≤ 1 мин) без постобработки — статус
   проходит `pending → transcribing → done`, результат содержит текст.
5. Повторить с постобработкой — статус проходит `processing → done`,
   текст отредактирован.

Полный план проверки — в `docs/SMOKE_TEST_PLAN.md`, типовые сбои — в
`docs/TROUBLESHOOTING.md`. Контракт HTTP API — в `backend/API_CONTRACT.md`.

# Transkreebatoriya

ИИ-агент для транскрибации аудио и видео файлов.  
Стек: **FastAPI** → **ffmpeg** → **faster-whisper** (`base`, всегда локально) → **LLM-постобработка** (локальная **Ollama** или облачный **OpenRouter** на выбор) → браузерный UI.

Архитектура агента следует спецификации [agentic-repository](../agentic-repository/AGENT_SPEC.md):
runtime-независимое ядро (промпты, контракты, каноническое поведение) — в [`core/`](core/),
упаковка под конкретный runtime — в [`runtimes/`](runtimes/), контракт агента — в [`manifest.yaml`](manifest.yaml).

---

## Требования

| Компонент | Версия | Установка |
|-----------|--------|-----------|
| uv | любая | `winget install astral-sh.uv` / [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| ffmpeg | любая | [ffmpeg.org](https://ffmpeg.org/download.html) → добавить в `PATH` |
| Ollama | любая (опционально — локальный провайдер постобработки) | [ollama.com](https://ollama.com) |
| OpenRouter | API-ключ (опционально — облачный провайдер постобработки) | [openrouter.ai/keys](https://openrouter.ai/keys) |

Python отдельно ставить не нужно — uv сам скачает нужную версию (3.12) из `.python-version`.

---

## Установка и запуск

### Локально

Инсталлятор проверяет зависимости, создаёт `.env` и `Modelfile` из шаблонов
(не перезаписывая существующие), ставит зависимости и скачивает модель Ollama:

```powershell
.\install.ps1        # Windows
./install.sh         # Linux / macOS
```

Проверка установки (вывод `[OK]/[WARN]/[FAIL]`):

```powershell
.\scripts\verify_install.ps1
./scripts/verify_install.sh
```

Запуск — один скрипт поднимает Ollama, модель и сервер:

```powershell
.\start-local.ps1
```

Или вручную — окружением управляет `uv run` (зависимости синхронизируются автоматически по `uv.lock`):

```powershell
uv run uvicorn backend.main:app --port 8001
```

### Docker

```powershell
git clone <repo-url>
cd transkreebatoriya-agent
docker compose up --build
```

Открыть в браузере: **http://localhost:8001**

Подробности: [DOCKER.md](DOCKER.md)

При первом запуске Docker соберёт образ приложения, Ollama скачает модель `qwen2.5:1.5b`
(или заданную в `OLLAMA_MODEL`), а faster-whisper скачает модель `base` (~140 МБ) при первой транскрибации.

---

## Управление Docker

```powershell
docker compose up --build
```

Остановить:

```powershell
docker compose down
```

Удалить контейнеры и скачанные Docker volumes:

```powershell
docker compose down -v
```

---

## Конфигурация

Все настройки читаются из переменных окружения (или файла `.env` в корне проекта)
и валидируются при старте (pydantic-settings). Шаблон с подробными комментариями —
`templates/env.example`; install-скрипт генерирует из него минимальный `.env`
(только переменные, без комментариев; существующий `.env` не перезаписывается).

Ключевые параметры:

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `LLM_PROVIDER` | `ollama` | Провайдер постобработки: `ollama` (локально, приватно) / `openrouter` (облако, быстро, текст уходит наружу) |
| `WHISPER_MODEL_NAME` | `base` | Модель faster-whisper: `tiny` / `base` / `small` / `medium` / `large-v3` |
| `WHISPER_DEVICE` | `auto` | Устройство: `auto` (CUDA если есть) / `cpu` / `cuda` |
| `WHISPER_LANGUAGE` | `ru` | Язык распознавания (ISO-639-1); `auto` — автоопределение |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Рекомендованная CPU-модель для постобработки (провайдер `ollama`) |
| `OLLAMA_KEEP_ALIVE` | `15m` | Держать модель прогретой между запросами |
| `OLLAMA_NUM_CTX` | `2048` | Контекст; больше на этом железе даёт лишний KV cache pressure |
| `OLLAMA_NUM_PREDICT` | `768` | Верхний предел вывода на один чанк |
| `OPENROUTER_API_KEY` | — | Ключ OpenRouter (openrouter.ai/keys), нужен при `LLM_PROVIDER=openrouter` |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v4-pro` | Модель постобработки (провайдер `openrouter`) |
| `OPENROUTER_TIMEOUT` | `300` | Таймаут одного запроса к OpenRouter (на чанк), сек |
| `POSTPROCESS_CONCURRENCY` | `1` | Параллельность чанков; для OpenRouter можно поднять до 4–8 |
| `POSTPROCESS_CHUNK_CHARS` | `1800` | Макс. символов в одном чанке, чтобы не разгонять prompt eval |
| `APP_PORT` | `8001` | Порт FastAPI сервера |
| `MAX_FILE_SIZE_GB` | `6` | Лимит размера файла в ГБ |
| `TASK_TTL_HOURS` | `24` | Сколько часов хранить завершённые задачи (результаты) в памяти |
| `HF_TOKEN` | — | Токен Hugging Face для ускоренной загрузки моделей |

Системный промпт постобработки живёт в [`core/prompts/postprocess.system.md`](core/prompts/postprocess.system.md)
(версионируется через frontmatter), а не в коде.

---

## Поддерживаемые форматы

`.mp3` `.mp4` `.wav` `.m4a` `.mkv` `.flac` `.ogg` `.webm` `.avi` `.mov`

Максимальный размер файла: **6 ГБ** (проверяется во время потоковой записи —
слишком большой файл отклоняется сразу, без полной записи на диск).

---

## Возможности UI

- **Drag-and-drop** или выбор файла через диалог
- **Прогресс-бар** с процентом выполнения
- **ETA** — показывает время, прошедшее с начала и примерное время до окончания
- **Переключатель постобработки** — можно отключить Ollama и получить сырой текст whisper быстрее
- **Копирование** результата в буфер обмена
- **Скачивание** транскрипции в формате `.md`

---

## Архитектура

```
[Браузер: drag-and-drop]
        ↓ POST /api/upload
[FastAPI: валидация + создание задачи]
        ↓ asyncio.to_thread
[ffmpeg → WAV 16kHz mono]
        ↓ asyncio.to_thread
[faster-whisper base, VAD-фильтр, INT8]
[Сырой текст + прогресс в реальном времени]
        ↓ (если постобработка включена)
[LLMClient → Ollama (локально) или OpenRouter (deepseek/deepseek-v4-pro)]
[Исправленный текст с пунктуацией и абзацами]
        ↓ GET /api/result / GET /api/download
[Браузер: прогресс → результат → копировать / скачать .md]
```

Нормативное поведение зафиксировано в core-контрактах:

- [`core/instructions.md`](core/instructions.md) — что агент должен и не должен делать
- [`core/contracts/pipeline_contract.md`](core/contracts/pipeline_contract.md) — статусы, прогресс, ETA, TTL
- [`core/contracts/postprocess_contract.md`](core/contracts/postprocess_contract.md) — чанкование, роль LLM
- [`core/contracts/error_contract.md`](core/contracts/error_contract.md) — таксономия ошибок

### Структура проекта

```
transkreebatoriya-agent/
├── manifest.yaml             # контракт агента (agentic-repository/AGENT_SPEC.md)
├── core/                     # runtime-независимое ядро
│   ├── README.md             # сценарии, возможности, ограничения
│   ├── instructions.md       # каноническое поведение (do/don't)
│   ├── prompts/
│   │   └── postprocess.system.md   # системный промпт LLM-редактора
│   └── contracts/            # нормативные контракты (pipeline, postprocess, errors)
├── runtimes/
│   └── local-web/
│       └── README.md         # установка, конфигурация, smoke test runtime
├── docs/
│   ├── SMOKE_TEST_PLAN.md
│   └── TROUBLESHOOTING.md
├── templates/                # шаблоны локальной конфигурации (placeholder-значения)
│   ├── env.example
│   └── Modelfile.cpu-qwen25-1.5b.template
├── scripts/
│   ├── verify_install.ps1 / .sh   # проверка установки [OK]/[WARN]/[FAIL]
├── install.ps1 / install.sh  # установка (never overwrite)
├── start-local.ps1           # однокомандный локальный запуск
├── backend/
│   ├── api/
│   │   ├── config.py         # GET  /api/config (публичные лимиты для клиентов)
│   │   ├── upload.py         # POST /api/upload (потоковая валидация размера)
│   │   ├── status.py         # GET  /api/status/{id}
│   │   └── result.py         # GET  /api/result/{id}, /api/download/{id}
│   ├── llm/
│   │   ├── base.py           # LLMClient — провайдеро-независимый интерфейс
│   │   ├── ollama.py         # OllamaClient (локальный провайдер)
│   │   └── openrouter.py     # OpenRouterClient (облачный провайдер)
│   ├── services/
│   │   ├── file_handler.py   # валидация, ffmpeg-конвертация
│   │   ├── transcription.py  # faster-whisper с прогрессом
│   │   └── postprocess.py    # чанкование, параллельность, через LLMClient
│   ├── tasks/
│   │   └── manager.py        # TaskManager (оркестрация, TTL-cleanup) + DI-провайдер
│   ├── settings.py           # настройки (pydantic-settings, валидация)
│   ├── config.py             # слой обратной совместимости (константы из settings)
│   ├── prompts.py            # загрузчик core-промптов
│   ├── models.py             # pydantic-модели ответов API
│   ├── exceptions.py         # иерархия доменных исключений
│   ├── API_CONTRACT.md       # контракт HTTP API
│   └── main.py               # FastAPI app, lifespan, middleware логирования
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── tests/                    # pytest-тесты (моки, не требуют сервера/Ollama/ffmpeg)
│   ├── test_manifest.py      # contract-тест: репозиторий ↔ manifest.yaml
│   ├── test_api.py           # API-слой (TestClient)
│   ├── test_process_task.py  # оркестрация пайплайна
│   ├── test_transcription.py # сервис транскрибации
│   ├── test_file_handler.py / test_manager.py / test_postprocess.py
│   └── integration/          # e2e против живого сервера (маркер integration)
├── Dockerfile
├── docker-compose.yml
└── DOCKER.md
```

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/config` | Публичные лимиты (форматы, макс. размер) для клиентов |
| `POST` | `/api/upload` | Загрузка файла, возвращает `task_id` |
| `GET` | `/api/status/{task_id}` | Статус + прогресс + ETA |
| `GET` | `/api/result/{task_id}` | JSON с `raw_text` и `processed_text` |
| `GET` | `/api/download/{task_id}` | Скачать `.md` файл |

Ответ `/api/status/{task_id}`:

```json
{
  "task_id": "...",
  "status": "transcribing",
  "progress": 42.5,
  "eta_seconds": 87,
  "elapsed_seconds": 34,
  "stage_message": "Транскрибация речи...",
  "error": null
}
```

Статусы задачи: `pending` → `transcribing` → `processing` → `done` / `error`

Завершённые задачи хранятся в памяти `TASK_TTL_HOURS` часов (дефолт 24),
затем удаляются; перезапуск сервера теряет результаты — скачивайте `.md` сразу.

Полный контракт: [backend/API_CONTRACT.md](backend/API_CONTRACT.md)

---

## Тестирование

```powershell
uv run pytest
```

Тесты не требуют запущенного сервера, Ollama или ffmpeg — используют моки.
В том числе: contract-тест `tests/test_manifest.py` проверяет соответствие
репозитория `manifest.yaml` (id, пути, core-файлы, отсутствие секретов).

Интеграционные тесты против живого сервера (нужны `TRANSKREE_INTEGRATION=1`,
запущенный сервер и файлы в `test_files/`):

```powershell
$env:TRANSKREE_INTEGRATION=1
uv run pytest -m integration
```

---

## Советы по ускорению

| Способ | Эффект |
|--------|--------|
| `LLM_PROVIDER=openrouter` | постобработка в 10–30× быстрее, чем на локальном CPU; текст уходит во внешний API |
| Модель `tiny` вместо `base` | ~2× быстрее, чуть ниже качество |
| GPU (CUDA) | 5–10× быстрее транскрибации |
| Отключить постобработку в UI | убирает этап LLM полностью |
| `POSTPROCESS_CONCURRENCY=4` (для openrouter) | параллельная обработка чанков |
| `OLLAMA_NUM_PARALLEL=1` + `POSTPROCESS_CONCURRENCY=1` (для ollama) | лучший latency/стабильность на `i5-1135G7` |
| `OLLAMA_KEEP_ALIVE=15m` | убирает лишние cold starts |
| `qwen2.5:1.5b` (ollama) | лучший баланс качества и скорости для локального CPU |
| `deepseek/deepseek-v4-pro` (openrouter) | качественная редактура; $0.435/$0.87 за 1M токенов in/out |
| Кастомный `transkreebatoriya-qwen25-cpu` | тот же базовый вес, но с зашитыми параметрами через `Modelfile` (рендерится install-скриптом из `templates/`) |

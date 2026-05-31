# Transkreebatoriya

ИИ-агент для транскрибации аудио и видео файлов.  
Стек: **FastAPI** → **ffmpeg** → **faster-whisper** (`base`) → **Ollama qwen3:4b** → браузерный UI.

---

## Требования

| Компонент | Версия | Установка |
|-----------|--------|-----------|
| Python | 3.10+ | [python.org](https://python.org) |
| ffmpeg | любая | [ffmpeg.org](https://ffmpeg.org/download.html) → добавить в `PATH` |
| Ollama | любая | [ollama.com](https://ollama.com) |
| qwen3:4b | — | `ollama pull qwen3:4b` |

---

## Установка и запуск

Docker:

```powershell
git clone <repo-url>
cd transkreebatoriya-agent
docker compose up --build
```

Открыть в браузере: **http://localhost:8001**

Подробности: [DOCKER.md](DOCKER.md)

При первом запуске Docker соберёт образ приложения, Ollama скачает модель `qwen3:4b`,
а faster-whisper скачает модель `base` (~140 МБ) при первой транскрибации.

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

Все настройки читаются из переменных окружения (или файла `.env` в корне проекта).  
Скопируйте `.env.example` как отправную точку:

```bat
copy .env.example .env
```

Ключевые параметры:

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `WHISPER_MODEL_NAME` | `base` | Модель faster-whisper: `tiny` / `base` / `small` / `medium` / `large-v3` |
| `WHISPER_DEVICE` | `auto` | Устройство: `auto` (CUDA если есть) / `cpu` / `cuda` |
| `OLLAMA_MODEL` | `qwen3:4b` | Модель Ollama для постобработки |
| `POSTPROCESS_CONCURRENCY` | `2` | Параллельность чанков (вместе с `OLLAMA_NUM_PARALLEL`) |
| `POSTPROCESS_CHUNK_CHARS` | `3000` | Макс. символов в одном чанке |
| `APP_PORT` | `8001` | Порт FastAPI сервера |
| `MAX_FILE_SIZE_GB` | `6` | Лимит размера файла в ГБ |
| `HF_TOKEN` | — | Токен Hugging Face для ускоренной загрузки моделей |

---

## Поддерживаемые форматы

`.mp3` `.mp4` `.wav` `.m4a` `.mkv` `.flac` `.ogg` `.webm` `.avi` `.mov`

Максимальный размер файла: **6 ГБ**

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
[Ollama qwen3:4b, think=False, параллельные чанки]
[Исправленный текст с пунктуацией и абзацами]
        ↓ GET /api/result / GET /api/download
[Браузер: прогресс → результат → копировать / скачать .md]
```

### Структура проекта

```
transkreebatoriya-agent/
├── backend/
│   ├── api/
│   │   ├── upload.py        # POST /api/upload
│   │   ├── status.py        # GET  /api/status/{id}
│   │   └── result.py        # GET  /api/result/{id}, /api/download/{id}
│   ├── services/
│   │   ├── file_handler.py  # валидация, ffmpeg-конвертация
│   │   ├── transcription.py # faster-whisper с прогрессом
│   │   └── postprocess.py   # Ollama, чанки, параллельность
│   ├── tasks/
│   │   └── manager.py       # TaskManager + DI-провайдер
│   ├── config.py            # настройки из .env / env vars
│   ├── exceptions.py        # иерархия доменных исключений
│   ├── main.py              # FastAPI app, middleware логирования
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── tests/                   # pytest-тесты
├── .env.example             # шаблон конфигурации
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
└── DOCKER.md
```

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
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

Полный контракт: [backend/API_CONTRACT.md](backend/API_CONTRACT.md)

---

## Тестирование

```powershell
docker compose run --rm app pytest
```

Тесты не требуют запущенного сервера, Ollama или ffmpeg — используют моки.

---

## Советы по ускорению

| Способ | Эффект |
|--------|--------|
| Модель `tiny` вместо `base` | ~2× быстрее, чуть ниже качество |
| GPU (CUDA) | 5–10× быстрее транскрибации |
| Отключить постобработку в UI | убирает этап Ollama полностью |
| `OLLAMA_NUM_PARALLEL=4` + `POSTPROCESS_CONCURRENCY=4` | ~2× быстрее постобработки |
| Модель `qwen2.5:1.5b` вместо `qwen3:4b` | ~3× быстрее Ollama, чуть ниже качество |

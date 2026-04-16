# Transkreebatoriya

ИИ-агент для транскрибации аудио и видео файлов.  
Стек: **FastAPI** → **ffmpeg** → **openai-whisper** (`base`) → **Ollama qwen3:4b** → браузерный UI.

---

## Требования

| Компонент | Версия | Установка |
|-----------|--------|-----------|
| Python | 3.10+ | python.org |
| ffmpeg | любая | [ffmpeg.org](https://ffmpeg.org/download.html) → добавить в `PATH` |
| Ollama | любая | [ollama.com](https://ollama.com) |
| qwen3:4b | — | `ollama pull qwen3:4b` |

---

## Установка

```bat
git clone <repo-url>
cd transkreebatoriya-agent\backend

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

При первом запуске whisper автоматически скачает модель `base` (~140 МБ).

---

## Запуск

### Быстрый старт (Windows)

```bat
start.bat
```

Скрипт проверяет доступность Ollama, наличие модели и запускает FastAPI сервер.

### Ручной запуск

```bat
REM 1. В отдельном терминале — Ollama (если не запущена как служба)
ollama serve

REM 2. Backend
cd backend
venv\Scripts\activate
python -m uvicorn main:app --host localhost --port 8000 --reload
```

Открыть в браузере: **http://localhost:8000**

---

## Поддерживаемые форматы

`.mp3` `.mp4` `.wav` `.m4a` `.mkv` `.flac` `.ogg` `.webm` `.avi` `.mov`

Максимальный размер файла: **6 ГБ**

---

## Архитектура

```
[Браузер: drag-and-drop]
        ↓ POST /api/upload
[FastAPI backend]
        ↓ ffmpeg
[WAV 16kHz mono]
        ↓ openai-whisper base
[Сырой текст]
        ↓ Ollama qwen3:4b
[Исправленный текст с пунктуацией и абзацами]
        ↓ GET /api/result / GET /api/download
[Браузер: отображение + копировать + скачать .md]
```

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/upload` | Загрузка файла, возвращает `task_id` |
| `GET` | `/api/status/{task_id}` | Статус: `pending` → `transcribing` → `processing` → `done` / `error` |
| `GET` | `/api/result/{task_id}` | JSON с `raw_text` и `processed_text` |
| `GET` | `/api/download/{task_id}` | Скачать `.md` файл |

Полный контракт: [backend/API_CONTRACT.md](backend/API_CONTRACT.md)

---

## Интеграционное тестирование

```bat
REM Положите тестовые файлы в папку test_files/
REM test_files/test.mp3, test_files/test.wav и т.д.

cd backend && venv\Scripts\activate && cd ..
python test_integration.py
```

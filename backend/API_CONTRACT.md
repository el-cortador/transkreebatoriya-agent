# API Контракт Transkreebatoriya

Контракт runtime `local-web`. Стадии, статусы и прогресс нормативно
описаны в `core/contracts/pipeline_contract.md`, ошибки — в
`core/contracts/error_contract.md`.

## Базовый URL
```
http://localhost:8001
```

## Эндпоинты

### 0. Конфигурация сервера
```
GET /api/config
```

Единый источник правды о лимитах для клиентов (UI читает его при загрузке
страницы вместо захардкоженных значений).

**Response (200):**
```json
{
  "allowed_extensions": [".avi", ".flac", ".m4a", ".mkv", ".mov", ".mp3", ".mp4", ".ogg", ".wav", ".webm"],
  "max_file_size_gb": 6,
  "postprocess_available": true
}
```

---

### 1. Загрузка файла
```
POST /api/upload
```

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (бинарный файл), `postprocess` (строка `"true"`/`"false"`, дефолт `"true"`)

**Response (200):**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "filename": "audio.mp3"
}
```

**Errors:**
- `400` — Неподдерживаемый формат / файл пустой / файл слишком большой
  (лимит проверяется во время потоковой записи, частичный файл удаляется)
- `500` — Внутренняя ошибка сервера

---

### 2. Проверка статуса
```
GET /api/status/{task_id}
```

**Response (200):**
```json
{
  "task_id": "uuid-string",
  "status": "transcribing",
  "progress": 42.5,
  "eta_seconds": 87,
  "elapsed_seconds": 34,
  "stage_message": "Транскрибация речи...",
  "error": null
}
```

- `progress` — 0–100, распределение по стадиям: см. `core/contracts/pipeline_contract.md`
- `eta_seconds` — оценка оставшегося времени или `null`, если данных недостаточно
- `elapsed_seconds` — секунд прошло с создания задачи
- `stage_message` — человекочитаемое описание текущей стадии

**Возможные статусы:**
- `pending` — в очереди
- `transcribing` — транскрибация
- `processing` — постобработка
- `done` — готово
- `error` — ошибка

**Errors:**
- `404` — Задача не найдена

---

### 3. Получение результата
```
GET /api/result/{task_id}
```

**Response (200):**
```json
{
  "task_id": "uuid-string",
  "raw_text": "сырой текст whisper",
  "processed_text": "обработанный текст Ollama"
}
```

**Errors:**
- `400` — Задача не завершена
- `404` — Задача не найдена

---

### 4. Скачивание результата
```
GET /api/download/{task_id}
```

**Response (200):**
- Content-Type: `text/markdown`
- Content-Disposition: `attachment; filename=audio_transcription.md`
- Body: обработанный текст в формате Markdown

**Errors:**
- `400` — Задача не завершена
- `404` — Задача не найдена (в т.ч. удалена по TTL — см. `core/contracts/pipeline_contract.md`, §4)

---

## Пример workflow

1. **Загрузка файла** → получаем `task_id`
2. **Polling `/api/status/{task_id}`** каждые 2 секунды
3. При статусе `done` → **`/api/result/{task_id}`** для получения текста
4. **Скачивание** → **`/api/download/{task_id}`**

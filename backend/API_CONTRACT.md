# API Контракт Transkreebatoriya

## Базовый URL
```
http://localhost:8000
```

## Эндпоинты

### 1. Загрузка файла
```
POST /api/upload
```

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (бинарный файл)

**Response (200):**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "filename": "audio.mp3"
}
```

**Errors:**
- `400` — Неподдерживаемый формат / файл слишком большой
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
  "error": null
}
```

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
- `404` — Задача не найдена

---

## Пример workflow

1. **Загрузка файла** → получаем `task_id`
2. **Polling `/api/status/{task_id}`** каждые 2 секунды
3. При статусе `done` → **`/api/result/{task_id}`** для получения текста
4. **Скачивание** → **`/api/download/{task_id}`**

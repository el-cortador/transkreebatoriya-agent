"""
Иерархия исключений приложения Transkreebatoriya.

Каждый слой (сервисы, API, задачи) поднимает типизированное исключение
из этого модуля. API-роутеры отображают их на конкретные HTTP-коды.
"""


class TranscribatoriyaError(Exception):
    """Базовый класс для всех доменных ошибок приложения."""


# ── Файлы ─────────────────────────────────────────────────────────────────────

class FileValidationError(TranscribatoriyaError):
    """Неверный формат, размер или содержимое загруженного файла."""


class ConversionError(TranscribatoriyaError):
    """Ошибка конвертации медиафайла через ffmpeg."""


# ── Транскрибация ─────────────────────────────────────────────────────────────

class TranscriptionError(TranscribatoriyaError):
    """Ошибка распознавания речи (faster-whisper)."""


# ── Постобработка ─────────────────────────────────────────────────────────────

class PostprocessError(TranscribatoriyaError):
    """Базовая ошибка постобработки через Ollama."""


class OllamaUnavailableError(PostprocessError):
    """Ollama недоступна (ошибка подключения)."""


class OllamaTimeoutError(PostprocessError):
    """Ollama не ответила в отведённое время."""


# ── Задачи ────────────────────────────────────────────────────────────────────

class TaskNotFoundError(TranscribatoriyaError):
    """Задача с указанным task_id не существует."""


class TaskNotReadyError(TranscribatoriyaError):
    """Задача ещё не завершена."""

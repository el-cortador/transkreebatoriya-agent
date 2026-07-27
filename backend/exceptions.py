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
    """Базовая ошибка постобработки через LLM."""


class OllamaUnavailableError(PostprocessError):
    """LLM-провайдер недоступен (ошибка подключения).

    Имя историческое: покрывает любой провайдер (Ollama, OpenRouter, ...).
    """


class OllamaTimeoutError(PostprocessError):
    """LLM-провайдер не ответил в отведённое время.

    Имя историческое: покрывает любой провайдер (Ollama, OpenRouter, ...).
    """


# ── Задачи ────────────────────────────────────────────────────────────────────

class TaskNotFoundError(TranscribatoriyaError):
    """Задача с указанным task_id не существует."""


class TaskNotReadyError(TranscribatoriyaError):
    """Задача ещё не завершена."""

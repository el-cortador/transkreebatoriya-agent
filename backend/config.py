"""
Конфигурация приложения — слой обратной совместимости.

Реальная реализация с валидацией: backend/settings.py (pydantic-settings).
Этот модуль ре-экспортирует значения как модульные константы, чтобы
существующие импорты `from backend.config import X` продолжали работать.

Новый код должен использовать `get_settings()` из backend/settings.py.
"""

from backend.settings import BASE_DIR, get_settings

_settings = get_settings()

# ── Директории ────────────────────────────────────────────────────────────────

TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# ── Whisper ───────────────────────────────────────────────────────────────────

WHISPER_MODEL_NAME: str = _settings.whisper_model_name
WHISPER_DEVICE: str = _settings.whisper_device
WHISPER_LANGUAGE: str = _settings.whisper_language

# ── ffmpeg ────────────────────────────────────────────────────────────────────

FFMPEG_PATH: str = _settings.ffmpeg_path

# ── Ollama ────────────────────────────────────────────────────────────────────

OLLAMA_API_URL: str = _settings.ollama_api_url
OLLAMA_MODEL: str = _settings.ollama_model
OLLAMA_KEEP_ALIVE: str = _settings.ollama_keep_alive
OLLAMA_NUM_CTX: int = _settings.ollama_num_ctx
OLLAMA_NUM_PREDICT: int = _settings.ollama_num_predict
OLLAMA_TEMPERATURE: float = _settings.ollama_temperature
OLLAMA_TOP_P: float = _settings.ollama_top_p
OLLAMA_TOP_K: int = _settings.ollama_top_k
OLLAMA_MIN_P: float = _settings.ollama_min_p
OLLAMA_REPEAT_LAST_N: int = _settings.ollama_repeat_last_n
OLLAMA_REPEAT_PENALTY: float = _settings.ollama_repeat_penalty
OLLAMA_TIMEOUT: int = _settings.ollama_timeout

# ── Постобработка ─────────────────────────────────────────────────────────────

POSTPROCESS_CHUNK_CHARS: int = _settings.postprocess_chunk_chars
POSTPROCESS_CONCURRENCY: int = _settings.postprocess_concurrency

# ── Лимиты файлов ─────────────────────────────────────────────────────────────

MAX_FILE_SIZE_GB: int = _settings.max_file_size_gb
MAX_FILE_SIZE: int = _settings.max_file_size_bytes

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3", ".mp4", ".wav", ".m4a", ".mkv",
    ".flac", ".ogg", ".webm", ".avi", ".mov",
})

# ── Задачи ────────────────────────────────────────────────────────────────────

TASK_TTL_SECONDS: float = _settings.task_ttl_seconds

# ── Сервер ────────────────────────────────────────────────────────────────────

APP_HOST: str = _settings.app_host
APP_PORT: int = _settings.app_port

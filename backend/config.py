"""
Конфигурация приложения.

Значения читаются из .env (если он есть), затем из переменных окружения.
Все параметры имеют разумные дефолты, поэтому .env необязателен.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Директории ────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# ── Whisper ───────────────────────────────────────────────────────────────────

# Варианты модели: tiny | base | small | medium | large-v3
# Чем больше модель — тем точнее, но медленнее.
WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "base")

# "auto" → CUDA если доступно, иначе CPU.
# Принудительно: "cpu" или "cuda".
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "auto")

# ── ffmpeg ────────────────────────────────────────────────────────────────────

FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")

# ── Ollama ────────────────────────────────────────────────────────────────────

OLLAMA_API_URL: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

# Варианты модели (по убыванию качества / возрастанию скорости):
#   qwen3:4b      — качество ★★★★, скорость ★★   (по умолчанию)
#   qwen2.5:1.5b  — качество ★★★,  скорость ★★★★
#   llama3.2:1b   — качество ★★,   скорость ★★★★★
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")

# Максимум символов в одном чанке постобработки
POSTPROCESS_CHUNK_CHARS: int = int(os.getenv("POSTPROCESS_CHUNK_CHARS", "3000"))

# Сколько чанков обрабатывать параллельно (требует OLLAMA_NUM_PARALLEL в окружении)
POSTPROCESS_CONCURRENCY: int = int(os.getenv("POSTPROCESS_CONCURRENCY", "2"))

# Таймаут одного запроса к Ollama в секундах (на один чанк)
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "1800"))

# ── Лимиты файлов ─────────────────────────────────────────────────────────────

MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE_GB", "6")) * 1024 * 1024 * 1024

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3", ".mp4", ".wav", ".m4a", ".mkv",
    ".flac", ".ogg", ".webm", ".avi", ".mov",
})

# ── Сервер ────────────────────────────────────────────────────────────────────

APP_HOST: str = os.getenv("APP_HOST", "localhost")
APP_PORT: int = int(os.getenv("APP_PORT", "8001"))

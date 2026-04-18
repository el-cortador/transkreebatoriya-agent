"""
Конфигурация приложения транскрибации.
"""

import os
from pathlib import Path

# Директории
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
TOOLS_DIR = BASE_DIR / "tools"

# whisper (faster-whisper)
WHISPER_MODEL_NAME = "base"
# "auto" → GPU если доступно (CUDA), иначе CPU.
# Принудительно "cpu" или "cuda" — задайте вручную.
WHISPER_DEVICE = "auto"

# ffmpeg
FFMPEG_PATH = "ffmpeg"  # Предполагается, что в PATH

# Ollama
OLLAMA_API_URL = "http://localhost:11434/api/generate"
#
# Модель постобработки. Варианты по убыванию качества / возрастанию скорости:
#   "qwen3:4b"      — качество ★★★★, скорость ★★   (по умолчанию)
#   "qwen2.5:1.5b"  — качество ★★★,  скорость ★★★★  (~3× быстрее)
#   "llama3.2:1b"   — качество ★★,   скорость ★★★★★ (~5× быстрее)
# Установка: ollama pull <название модели>
OLLAMA_MODEL = "qwen3.5:0.8b"

# Максимальный размер одного чанка для постобработки (символы).
POSTPROCESS_CHUNK_CHARS = 3000

# Сколько чанков обрабатывать параллельно.
# Требует OLLAMA_NUM_PARALLEL=<N> в окружении (задаётся в start.bat).
# На большинстве CPU оптимально 2 — выше не ускорит, только увеличит RAM.
POSTPROCESS_CONCURRENCY = 2

# Лимиты
MAX_FILE_SIZE = 6 * 1024 * 1024 * 1024  # 6 ГБ
ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".mkv", ".flac", ".ogg", ".webm", ".avi", ".mov"}

# Временные файлы
TEMP_DIR.mkdir(exist_ok=True)

"""
Конфигурация приложения транскрибации.
"""

import os
from pathlib import Path

# Директории
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
TOOLS_DIR = BASE_DIR / "tools"

# whisper (Python openai-whisper)
WHISPER_MODEL_NAME = "base"

# ffmpeg
FFMPEG_PATH = "ffmpeg"  # Предполагается, что в PATH

# Ollama
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"

# Лимиты
MAX_FILE_SIZE = 6 * 1024 * 1024 * 1024  # 6 ГБ
ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".mkv", ".flac", ".ogg", ".webm", ".avi", ".mov"}

# Временные файлы
TEMP_DIR.mkdir(exist_ok=True)

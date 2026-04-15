"""
Сервис транскрибации через whisper.cpp.
"""

import subprocess
import logging
from pathlib import Path
from config import WHISPER_CPP_PATH, WHISPER_MODEL_PATH

logger = logging.getLogger(__name__)


async def transcribe_audio(wav_path: Path) -> str:
    """
    Транскрибирует аудиофайл через whisper.cpp CLI.
    
    Args:
        wav_path: Путь к WAV файлу
        
    Returns:
        Сырой текст транскрибации
    """
    if not WHISPER_CPP_PATH.exists():
        raise RuntimeError(f"whisper.cpp не найден: {WHISPER_CPP_PATH}")
    
    if not WHISPER_MODEL_PATH.exists():
        raise RuntimeError(f"Модель whisper не найдена: {WHISPER_MODEL_PATH}")
    
    cmd = [
        str(WHISPER_CPP_PATH),
        "-m", str(WHISPER_MODEL_PATH),
        "-f", str(wav_path),
        "--output-txt"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 час максимум
            check=True
        )
        
        # Читаем выходной файл (whisper создаёт .txt с тем же именем)
        output_txt = wav_path.with_suffix(".txt")
        if output_txt.exists():
            return output_txt.read_text(encoding="utf-8")
        else:
            return result.stdout
            
    except subprocess.TimeoutExpired:
        logger.error("Транскрибация превысила таймаут")
        raise RuntimeError("Превышено время транскрибации")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка whisper.cpp: {e.stderr}")
        raise RuntimeError(f"Ошибка транскрибации: {e.stderr}")

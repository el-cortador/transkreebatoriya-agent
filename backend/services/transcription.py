"""
Сервис транскрибации через openai-whisper.
"""

import whisper
import logging
from pathlib import Path
from config import WHISPER_MODEL_NAME

logger = logging.getLogger(__name__)

# Глобальная модель (загружается один раз)
_model = None


def _load_model():
    """Ленивая загрузка модели."""
    global _model
    if _model is None:
        logger.info(f"Загрузка модели whisper {WHISPER_MODEL_NAME}...")
        _model = whisper.load_model(WHISPER_MODEL_NAME)
        logger.info("Модель загружена.")
    return _model


async def transcribe_audio(wav_path: Path) -> str:
    """
    Транскрибирует аудиофайл через openai-whisper.
    
    Args:
        wav_path: Путь к WAV файлу
        
    Returns:
        Сырой текст транскрибации
    """
    model = _load_model()
    
    if not wav_path.exists():
        raise RuntimeError(f"Аудиофайл не найден: {wav_path}")
    
    try:
        result = model.transcribe(str(wav_path), language="ru", fp16=False)
        return result.get("text", "").strip()
    except Exception as e:
        logger.error(f"Ошибка транскрибации: {str(e)}")
        raise RuntimeError(f"Ошибка транскрибации: {str(e)}")

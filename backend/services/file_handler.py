"""
Сервис обработки файлов: валидация и конвертация через ffmpeg.
"""

import subprocess
import logging
from pathlib import Path
from config import FFMPEG_PATH, ALLOWED_EXTENSIONS, MAX_FILE_SIZE

logger = logging.getLogger(__name__)


def validate_file(file_path: Path, filename: str) -> None:
    """
    Валидирует загруженный файл.
    
    Args:
        file_path: Путь к файлу
        filename: Имя файла
        
    Raises:
        ValueError: Если файл невалиден
    """
    ext = Path(filename).suffix.lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Неподдерживаемый формат файла. Поддерживаемые: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024**3):.1f} ГБ")
    
    if file_size == 0:
        raise ValueError("Файл пустой")


async def convert_to_wav(input_path: Path) -> Path:
    """
    Конвертирует аудио/видео файл в WAV через ffmpeg.
    
    Args:
        input_path: Путь к исходному файлу
        
    Returns:
        Путь к WAV файлу
    """
    output_path = input_path.with_suffix(".wav")
    
    cmd = [
        FFMPEG_PATH,
        "-i", str(input_path),
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",           # 16kHz (оптимально для whisper)
        "-ac", "1",               # Моно
        "-y",                     # Перезаписать выходной файл
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 минут
            check=True
        )
        logger.info(f"Конвертация завершена: {output_path}")
        return output_path
        
    except subprocess.TimeoutExpired:
        logger.error("Конвертация превысила таймаут")
        raise RuntimeError("Превышено время конвертации файла")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка ffmpeg: {e.stderr}")
        raise RuntimeError(f"Ошибка конвертации файла: {e.stderr}")

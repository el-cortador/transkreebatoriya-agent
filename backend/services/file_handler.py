"""
Сервис обработки файлов: валидация и конвертация через ffmpeg.
"""

import asyncio
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
        filename: Оригинальное имя файла (для проверки расширения)

    Raises:
        ValueError: Если файл невалиден
    """
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Неподдерживаемый формат файла. Поддерживаемые: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise ValueError("Файл пустой")
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024**3):.1f} ГБ")


async def convert_to_wav(input_path: Path) -> Path:
    """
    Конвертирует аудио/видео файл в WAV через ffmpeg.

    Запускает subprocess.run в пуле потоков через asyncio.to_thread,
    чтобы не блокировать event loop и избежать проблем с ProactorEventLoop на Windows.

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
        "-ar", "16000",           # 16 kHz — оптимально для whisper
        "-ac", "1",               # моно
        "-y",                     # перезаписать, если существует
        str(output_path),
    ]

    def _run() -> Path:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Превышено время конвертации файла")

        if result.returncode != 0:
            err_msg = result.stderr.decode("utf-8", errors="replace").strip()
            logger.error(f"Ошибка ffmpeg (код {result.returncode}): {err_msg}")
            raise RuntimeError(f"Ошибка конвертации файла: {err_msg}")

        logger.info(f"Конвертация завершена: {output_path}")
        return output_path

    return await asyncio.to_thread(_run)

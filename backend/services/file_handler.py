"""
Сервис обработки файлов: валидация и конвертация через ffmpeg.
"""

import asyncio
import subprocess
import logging
from pathlib import Path

from config import FFMPEG_PATH, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from exceptions import FileValidationError, ConversionError

logger = logging.getLogger(__name__)


def validate_file(file_path: Path, filename: str) -> None:
    """
    Валидирует загруженный файл.

    Raises:
        FileValidationError: Если файл невалиден (формат, размер, пустой).
    """
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Неподдерживаемый формат файла. Поддерживаемые: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise FileValidationError("Файл пустой")
    if file_size > MAX_FILE_SIZE:
        raise FileValidationError(f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024**3):.1f} ГБ")


async def convert_to_wav(input_path: Path) -> Path:
    """
    Конвертирует аудио/видео файл в WAV через ffmpeg.

    Запускает subprocess.run в пуле потоков через asyncio.to_thread,
    чтобы не блокировать event loop и избежать проблем с ProactorEventLoop на Windows.

    Raises:
        ConversionError: Если ffmpeg завершился с ошибкой или превышен таймаут.
    """
    output_path = input_path.with_suffix(".wav")

    cmd = [
        FFMPEG_PATH,
        "-fflags", "+discardcorrupt",  # пропускать битые пакеты вместо отказа
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
            raise ConversionError("Превышено время конвертации файла")

        # ffmpeg может вернуть ненулевой код при наличии битых пакетов в исходнике,
        # но при этом всё равно записать корректный WAV. Считаем конвертацию
        # успешной, если выходной файл создан и непустой.
        wav_ok = output_path.exists() and output_path.stat().st_size > 0
        if result.returncode != 0:
            if wav_ok:
                logger.warning(
                    f"[file_handler] ffmpeg завершился с кодом {result.returncode} "
                    f"(битые пакеты в исходнике), но WAV создан — продолжаем."
                )
            else:
                err_msg = result.stderr.decode("utf-8", errors="replace").strip()
                # Берём последние 500 символов чтобы не перегружать лог
                logger.error(f"[file_handler] ffmpeg ошибка (код {result.returncode}): {err_msg[-500:]}")
                raise ConversionError(f"Ошибка конвертации файла (код {result.returncode})")

        logger.info(f"[file_handler] Конвертация завершена: {output_path.name}")
        return output_path

    return await asyncio.to_thread(_run)

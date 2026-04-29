"""
Сервис транскрибации через faster-whisper.

Преимущества faster-whisper перед openai-whisper:
  - ~4× быстрее на CPU (INT8-квантизация через CTranslate2)
  - Реальный прогресс: сегменты выдаются по мере обработки
  - Встроенный VAD-фильтр: пропускает тишину → значительный прирост скорости
    для записей с паузами (совещания, интервью)
  - Автоопределение GPU (CUDA)
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable, Optional

from config import WHISPER_MODEL_NAME, WHISPER_DEVICE
from exceptions import TranscriptionError

logger = logging.getLogger(__name__)

# Глобальная модель (загружается один раз при первом обращении)
_model = None


def _load_model():
    """Ленивая загрузка модели (вызывается в пуле потоков)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        import torch

        if WHISPER_DEVICE == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device = WHISPER_DEVICE

        compute_type = "float16" if device == "cuda" else "int8"
        logger.info(
            f"[transcription] Загрузка faster-whisper '{WHISPER_MODEL_NAME}' "
            f"(device={device}, compute={compute_type})..."
        )
        _model = WhisperModel(
            WHISPER_MODEL_NAME,
            device=device,
            compute_type=compute_type,
        )
        logger.info("[transcription] Модель faster-whisper загружена.")
    return _model


# Тип коллбека прогресса: (pct 0–100, eta_seconds | None)
ProgressCb = Callable[[float, Optional[int]], None]


def _do_transcribe(
    wav_path_str: str,
    progress_state: dict,
) -> str:
    """
    Синхронная транскрибация — запускается в пуле потоков.

    Обновляет progress_state["pct"] и progress_state["eta"] по мере
    обработки каждого сегмента. Это позволяет основному event loop читать
    актуальный прогресс без блокировок.

    Args:
        wav_path_str:   Путь к WAV-файлу.
        progress_state: Разделяемый dict { pct, eta, done }.
    """
    model = _load_model()

    segments, info = model.transcribe(
        wav_path_str,
        language="ru",
        beam_size=5,
        vad_filter=True,           # пропускать тишину
        vad_parameters={
            "min_silence_duration_ms": 500,
        },
    )

    total_duration = max(info.duration, 1.0)
    texts: list[str] = []
    start_wall = time.monotonic()

    for segment in segments:  # генератор — каждый сегмент готов сразу по мере обработки
        texts.append(segment.text)

        elapsed = time.monotonic() - start_wall
        audio_processed = segment.end
        if audio_processed > 0 and elapsed > 0:
            # Фактическая скорость обработки (сколько секунд реального времени
            # нужно, чтобы обработать 1 секунду аудио)
            rate = elapsed / audio_processed
            remaining_audio = total_duration - audio_processed
            progress_state["eta"] = max(0, int(remaining_audio * rate))
        progress_state["pct"] = min(99.0, audio_processed / total_duration * 100)

    progress_state["done"] = True
    return " ".join(texts).strip()


async def transcribe_audio(
    wav_path: Path,
    on_progress: Optional[ProgressCb] = None,
) -> str:
    """
    Транскрибирует аудиофайл через faster-whisper.

    Запускает тяжёлую CPU-операцию в пуле потоков через asyncio.to_thread.
    Прогресс реальный: основан на позиции обработанного сегмента в аудио.

    Raises:
        TranscriptionError: Если файл не найден или транскрибация завершилась с ошибкой.
    """
    if not wav_path.exists():
        raise TranscriptionError(f"Аудиофайл не найден: {wav_path}")

    # Разделяемое состояние между рабочим потоком (запись) и event loop (чтение)
    progress_state: dict = {"pct": 0.0, "eta": None, "done": False}
    stop_event = asyncio.Event()

    async def _flush_ticker():
        """Каждые 1.5 сек доставляет прогресс из рабочего потока в callback."""
        while not stop_event.is_set():
            await asyncio.sleep(1.5)
            if on_progress:
                on_progress(progress_state["pct"], progress_state.get("eta"))

    ticker = asyncio.create_task(_flush_ticker())

    try:
        result = await asyncio.to_thread(_do_transcribe, str(wav_path), progress_state)
    except TranscriptionError:
        raise
    except Exception as e:
        logger.error(f"[transcription] Ошибка: {e}")
        raise TranscriptionError(f"Ошибка транскрибации: {e}") from e
    finally:
        stop_event.set()
        ticker.cancel()
        try:
            await ticker
        except asyncio.CancelledError:
            pass

    if on_progress:
        on_progress(100.0, 0)

    logger.info("[transcription] Завершено успешно.")
    return result

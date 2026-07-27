"""
Сервис постобработки текста через LLM.

Длинные транскрипции разбиваются на чанки и обрабатываются параллельно
(POSTPROCESS_CONCURRENCY штук одновременно). При повышении параллельности
Ollama должна быть запущена с OLLAMA_NUM_PARALLEL=N (см. install.ps1 /
docker-compose.yml).

Системный промпт загружается из core/prompts/postprocess.system.md.
Провайдер LLM инкапсулирован за LLMClient (backend/llm/).
Нормативное поведение: core/contracts/postprocess_contract.md.
"""

import asyncio
import re
import logging
import time
from typing import Callable, Optional

import httpx

from backend.config import POSTPROCESS_CHUNK_CHARS, POSTPROCESS_CONCURRENCY
from backend.exceptions import OllamaUnavailableError, OllamaTimeoutError, PostprocessError
from backend.llm import LLMClient, get_llm_client
from backend.prompts import get_postprocess_system_prompt

logger = logging.getLogger(__name__)

# Начальная оценка секунд на один чанк до получения реальных данных
_INITIAL_CHUNK_SEC = 60.0


def _strip_thinking(text: str) -> str:
    """Удаляет <think>...</think> блоки qwen3 chain-of-thought."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _split_into_chunks(text: str, max_chars: int = POSTPROCESS_CHUNK_CHARS) -> list[str]:
    """
    Разбивает текст на чанки не длиннее max_chars символов по границам предложений.
    """
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


async def _process_chunk(chunk: str, system: str, llm: LLMClient) -> str:
    """Обрабатывает один чанк через LLM и нормализует ответ (think-strip)."""
    raw = await llm.generate(chunk, system=system)
    return _strip_thinking(raw)


async def postprocess_text(
    raw_text: str,
    on_progress: Optional[Callable[[float, Optional[int]], None]] = None,
    llm: Optional[LLMClient] = None,
) -> str:
    """
    Постобрабатывает транскрипцию через LLM с параллельной обработкой чанков.

    POSTPROCESS_CONCURRENCY чанков обрабатываются одновременно.
    Прогресс и ETA обновляются по завершении каждого чанка.

    Args:
        raw_text:    Сырой текст транскрибации.
        on_progress: Callback (pct 0–100, eta_seconds | None).
        llm:         LLM-клиент; по умолчанию — разделяемый клиент из get_llm_client().

    Raises:
        OllamaUnavailableError: Если LLM-сервис недоступен.
        OllamaTimeoutError:     Если LLM не ответила вовремя.
        PostprocessError:       Прочие ошибки постобработки.
    """
    llm = llm or get_llm_client()
    system = get_postprocess_system_prompt()

    chunks = _split_into_chunks(raw_text)
    total = len(chunks)

    if total > 1:
        logger.info(
            f"[postprocess] {total} чанков, "
            f"параллельность={POSTPROCESS_CONCURRENCY} "
            f"(~{len(raw_text) // total} симв/чанк)"
        )

    results: list[Optional[str]] = [None] * total

    # Разделяемое состояние для прогресса (пишется из корутин, читается из них же — event loop один)
    completed: list[int] = [0]
    chunk_durations: list[float] = []

    sem = asyncio.Semaphore(POSTPROCESS_CONCURRENCY)

    async def process_one(idx: int, chunk: str) -> None:
        async with sem:
            wall_start = time.monotonic()
            logger.info(f"[postprocess] Чанк {idx + 1}/{total}...")

            result = await _process_chunk(chunk, system, llm)

            elapsed = time.monotonic() - wall_start
            chunk_durations.append(elapsed)
            completed[0] += 1
            results[idx] = result

            if on_progress:
                done_pct = completed[0] / total * 100
                avg = sum(chunk_durations) / len(chunk_durations)
                remaining_chunks = total - completed[0]
                eta = int(avg * remaining_chunks)
                on_progress(done_pct, eta)

    try:
        await asyncio.gather(*[process_one(i, c) for i, c in enumerate(chunks)])
    except httpx.TimeoutException as e:
        logger.error("[postprocess] LLM timeout")
        raise OllamaTimeoutError("Превышено время постобработки текста") from e
    except httpx.ConnectError as e:
        logger.error("[postprocess] LLM-провайдер недоступен")
        raise OllamaUnavailableError("LLM-сервис постобработки недоступен") from e
    except Exception as e:
        logger.error(f"[postprocess] Ошибка: {e}")
        raise PostprocessError(f"Ошибка постобработки текста: {e}") from e

    if on_progress:
        on_progress(100.0, 0)

    logger.info("[postprocess] Завершено успешно.")
    return "\n\n".join(r for r in results if r is not None)

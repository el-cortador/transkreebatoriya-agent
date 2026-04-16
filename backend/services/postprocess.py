"""
Сервис постобработки текста через Ollama.

Длинные транскрипции разбиваются на чанки и обрабатываются параллельно
(POSTPROCESS_CONCURRENCY штук одновременно). Ollama должна быть запущена
с OLLAMA_NUM_PARALLEL=N — задаётся в start.bat.
"""

import asyncio
import json
import re
import logging
import time
from typing import Callable, Optional

import httpx

from config import OLLAMA_API_URL, OLLAMA_MODEL, POSTPROCESS_CHUNK_CHARS, POSTPROCESS_CONCURRENCY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — профессиональный редактор транскрибаций. Твоя задача — улучшить качество текста, полученного через распознавание речи.

Исходные данные: сырой текст, полученный через whisper (может содержать ошибки распознавания, отсутствовать пунктуацию, быть разбитым на неправильные абзацы).

Что нужно сделать:
1. Исправить ошибки распознавания (неправильные слова, искажённые фамилии, термины).
2. Расставить знаки препинания там, где они отсутствуют.
3. Разбить текст на логические абзацы.
4. Если в тексте есть диалог или несколько спикеров, разметить их как "Спикер 1:", "Спикер 2:" и т.д. (на основе контекста, не обязательно точно).
5. Сохранить исходный смысл, не добавлять и не убирать информацию.

Верни только обработанный текст, без дополнительных комментариев и пояснений."""

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


async def _process_chunk(chunk: str) -> str:
    """Обрабатывает один чанк через Ollama со стримингом."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": chunk,
        "system": SYSTEM_PROMPT,
        "stream": True,
        "think": False,  # отключаем chain-of-thought у qwen3
    }

    collected: list[str] = []
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", OLLAMA_API_URL, json=payload, timeout=600.0) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                collected.append(data.get("response", ""))

    return _strip_thinking("".join(collected))


async def postprocess_text(
    raw_text: str,
    on_progress: Optional[Callable[[float, Optional[int]], None]] = None,
) -> str:
    """
    Постобрабатывает транскрипцию через Ollama с параллельной обработкой чанков.

    POSTPROCESS_CONCURRENCY чанков обрабатываются одновременно.
    Прогресс и ETA обновляются по завершении каждого чанка.

    Args:
        raw_text:    Сырой текст транскрибации.
        on_progress: Callback(pct: 0–100, eta_seconds | None).
    """
    chunks = _split_into_chunks(raw_text)
    total = len(chunks)

    if total > 1:
        logger.info(
            f"Постобработка: {total} чанков, "
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
            logger.info(f"Постобработка чанка {idx + 1}/{total}...")

            try:
                result = await _process_chunk(chunk)
            except Exception:
                raise

            elapsed = time.monotonic() - wall_start
            chunk_durations.append(elapsed)
            completed[0] += 1
            results[idx] = result

            # Обновляем прогресс и ETA после завершения чанка
            if on_progress:
                done_pct = completed[0] / total * 100
                avg = sum(chunk_durations) / len(chunk_durations)
                remaining_chunks = total - completed[0]
                eta = int(avg * remaining_chunks)
                on_progress(done_pct, eta)

    try:
        await asyncio.gather(*[process_one(i, c) for i, c in enumerate(chunks)])
    except httpx.TimeoutException:
        logger.error("Ollama timeout")
        raise RuntimeError("Превышено время постобработки текста")
    except httpx.ConnectError:
        logger.error("Ollama недоступна")
        raise RuntimeError("Сервис Ollama недоступен")
    except Exception as e:
        logger.error(f"Ошибка Ollama: {e}")
        raise RuntimeError(f"Ошибка постобработки текста: {e}")

    if on_progress:
        on_progress(100.0, 0)

    return "\n\n".join(r for r in results if r is not None)

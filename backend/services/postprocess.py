"""
Сервис постобработки текста через Ollama.
"""

import httpx
import logging
from config import OLLAMA_API_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# Системный промпт для постобработки
SYSTEM_PROMPT = """Ты — профессиональный редактор транскрибаций. Твоя задача — улучшить качество текста, полученного через распознавание речи.

Исходные данные: сырой текст, полученный через whisper (может содержать ошибки распознавания, отсутствовать пунктуацию, быть разбитым на неправильные абзацы).

Что нужно сделать:
1. Исправить ошибки распознавания (неправильные слова, искажённые фамилии, термины).
2. Расставить знаки препинания там, где они отсутствуют.
3. Разбить текст на логические абзацы.
4. Если в тексте есть диалог или несколько спикеров, разметить их как "Спикер 1:", "Спикер 2:" и т.д. (на основе контекста, не обязательно точно).
5. Сохранить исходный смысл, не добавлять и не убирать информацию.

Верни только обработанный текст, без дополнительных комментариев и пояснений."""


async def postprocess_text(raw_text: str) -> str:
    """
    Отправляет сырой текст в Ollama для постобработки.
    
    Args:
        raw_text: Сырой текст транскрибации
        
    Returns:
        Обработанный текст
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": raw_text,
        "system": SYSTEM_PROMPT,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OLLAMA_API_URL,
                json=payload,
                timeout=300.0  # 5 минут
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
            
    except httpx.TimeoutException:
        logger.error("Ollama timeout: постобработка не удалась")
        raise RuntimeError("Превышено время постобработки текста")
    except httpx.ConnectError:
        logger.error("Ollama недоступна: не удалось подключиться")
        raise RuntimeError("Сервис Ollama недоступен")
    except Exception as e:
        logger.error(f"Ошибка Ollama: {str(e)}")
        raise RuntimeError(f"Ошибка постобработки текста: {str(e)}")

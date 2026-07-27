"""
LLM-клиенты: провайдеро-независимый интерфейс + реализации.

get_llm_client() возвращает разделяемый синглтон (переиспользует HTTP-соединения),
close_llm_client() вызывается при остановке приложения.
"""

from typing import Optional

from backend.llm.base import LLMClient
from backend.llm.ollama import OllamaClient

__all__ = ["LLMClient", "OllamaClient", "get_llm_client", "close_llm_client"]

_default_client: Optional[OllamaClient] = None


def get_llm_client() -> OllamaClient:
    """Разделяемый LLM-клиент по умолчанию (Ollama)."""
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient()
    return _default_client


async def close_llm_client() -> None:
    """Закрыть разделяемый клиент (вызывается из lifespan при shutdown)."""
    global _default_client
    if _default_client is not None:
        await _default_client.aclose()
        _default_client = None

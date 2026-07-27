"""
LLM-клиенты: провайдеро-независимый интерфейс + реализации.

get_llm_client() возвращает разделяемый синглтон провайдера из настроек
(LLM_PROVIDER: ollama | openrouter), close_llm_client() вызывается при
остановке приложения.
"""

from typing import Optional

from backend.llm.base import LLMClient
from backend.llm.ollama import OllamaClient
from backend.llm.openrouter import OpenRouterClient
from backend.settings import get_settings

__all__ = ["LLMClient", "OllamaClient", "OpenRouterClient", "get_llm_client", "close_llm_client"]

_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Разделяемый LLM-клиент провайдера из настроек (LLM_PROVIDER)."""
    global _default_client
    if _default_client is None:
        settings = get_settings()
        if settings.llm_provider == "openrouter":
            _default_client = OpenRouterClient(settings)
        else:
            _default_client = OllamaClient(settings)
    return _default_client


async def close_llm_client() -> None:
    """Закрыть разделяемый клиент (вызывается из lifespan при shutdown)."""
    global _default_client
    if _default_client is not None:
        await _default_client.aclose()
        _default_client = None

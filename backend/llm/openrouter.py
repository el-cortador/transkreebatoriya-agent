"""
LLM-клиент для OpenRouter (OpenAI-совместимый chat completions API).

Используется при LLM_PROVIDER=openrouter: текст транскрипции уходит во
внешний API — это осознанный opt-in пользователя (см. core/instructions.md).
Аудио при этом всегда остаётся локальным (транскрибация — faster-whisper).

Единый httpx.AsyncClient переиспользуется между запросами и задачами.
"""

import logging
from typing import Optional

import httpx

from backend.exceptions import PostprocessError
from backend.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """LLMClient для OpenRouter. Ошибки httpx пробрасываются наверх нетронутыми —
    их отображение на доменные исключения делает сервис постобработки."""

    def __init__(self, settings: Optional[Settings] = None):
        s = settings or get_settings()
        if not s.openrouter_api_key:
            raise PostprocessError(
                "LLM_PROVIDER=openrouter, но OPENROUTER_API_KEY не задан. "
                "Получите ключ: https://openrouter.ai/keys"
            )
        self._url = f"{s.openrouter_base_url.rstrip('/')}/chat/completions"
        self._model = s.openrouter_model
        self._timeout = float(s.openrouter_timeout)
        self._headers = {
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        self._defaults = {
            "temperature": s.openrouter_temperature,
            "max_tokens": s.openrouter_max_tokens,
        }
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Ленивая создание разделяемого HTTP-клиента (внутри event loop)."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def generate(self, prompt: str, *, system: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            # Задача — редактура, рассуждения не нужны: быстрее и дешевле
            "reasoning": {"exclude": True},
            **self._defaults,
        }

        client = self._get_client()
        response = await client.post(
            self._url, json=payload, headers=self._headers, timeout=self._timeout
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

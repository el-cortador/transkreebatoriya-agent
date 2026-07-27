"""
LLM-клиент для Ollama (протокол /api/generate со стримингом).

Единый httpx.AsyncClient переиспользуется между запросами и задачами —
соединение не пересоздаётся на каждый чанк.
"""

import json
import logging
from typing import Optional

import httpx

from backend.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """LLMClient для Ollama. Ошибки httpx пробрасываются наверх нетронутыми —
    их отображение на доменные исключения делает сервис постобработки."""

    def __init__(self, settings: Optional[Settings] = None):
        s = settings or get_settings()
        self._api_url = s.ollama_api_url
        self._model = s.ollama_model
        self._keep_alive = s.ollama_keep_alive
        self._timeout = float(s.ollama_timeout)
        self._options = {
            "num_ctx": s.ollama_num_ctx,
            "num_predict": s.ollama_num_predict,
            "temperature": s.ollama_temperature,
            "top_p": s.ollama_top_p,
            "top_k": s.ollama_top_k,
            "min_p": s.ollama_min_p,
            "repeat_last_n": s.ollama_repeat_last_n,
            "repeat_penalty": s.ollama_repeat_penalty,
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
            "prompt": prompt,
            "system": system,
            "stream": True,
            "think": False,  # отключаем chain-of-thought у qwen3
            "keep_alive": self._keep_alive,
            "options": self._options,
        }

        collected: list[str] = []
        client = self._get_client()
        async with client.stream("POST", self._api_url, json=payload, timeout=self._timeout) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                collected.append(data.get("response", ""))

        return "".join(collected)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

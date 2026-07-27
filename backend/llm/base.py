"""
Абстракция LLM-клиента.

Провайдеро-независимый интерфейс для стадии постобработки: сервис работает
с LLMClient, конкретный протокол (Ollama /api/generate и т.п.) инкапсулирован
в реализациях. См. core/contracts/postprocess_contract.md, §6.
"""

from typing import Protocol


class LLMClient(Protocol):
    """Минимальный контракт LLM-провайдера для текстовой постобработки."""

    async def generate(self, prompt: str, *, system: str) -> str:
        """
        Сгенерировать ответ на prompt с системной инструкцией system.

        Returns:
            Сырой текст ответа модели (нормализация — на стороне вызывающего).
        """
        ...

    async def aclose(self) -> None:
        """Освободить ресурсы (HTTP-соединения)."""
        ...

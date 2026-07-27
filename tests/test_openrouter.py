"""
Тесты OpenRouter LLM-клиента и фабрики провайдеров.

HTTP мокается на уровне разделяемого клиента — проверяется формирование
OpenAI-совместимого payload, заголовок авторизации и разбор ответа.
"""

import pytest

import backend.llm as llm_module
from backend.exceptions import PostprocessError
from backend.llm import OllamaClient, OpenRouterClient, get_llm_client
from backend.settings import Settings


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeHttp:
    """Подменный httpx.AsyncClient: записывает запросы, отвечает заготовленным JSON."""

    def __init__(self, payload: dict):
        self._payload = payload
        self.requests = []

    async def post(self, url, *, json=None, headers=None, timeout=None):
        self.requests.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse(self._payload)

    async def aclose(self):
        pass


def make_settings(**overrides) -> Settings:
    base = {"openrouter_api_key": "sk-or-test-key"}
    base.update(overrides)
    return Settings(**base)


def make_client(settings: Settings, response_payload: dict | None = None):
    payload = response_payload or {
        "choices": [{"message": {"content": "отредактированный текст"}}]
    }
    client = OpenRouterClient(settings)
    fake_http = FakeHttp(payload)
    client._client = fake_http
    return client, fake_http


# ── Запрос ────────────────────────────────────────────────────────────────────


async def test_generate_builds_openai_compatible_request():
    client, http = make_client(make_settings())

    result = await client.generate("кусок транскрипта", system="системный промпт")

    assert result == "отредактированный текст"
    assert len(http.requests) == 1
    req = http.requests[0]
    assert req["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert req["json"]["model"] == "deepseek/deepseek-v4-pro"
    assert req["json"]["messages"] == [
        {"role": "system", "content": "системный промпт"},
        {"role": "user", "content": "кусок транскрипта"},
    ]


async def test_generate_sends_auth_header_and_reasoning_excluded():
    client, http = make_client(make_settings())

    await client.generate("текст", system="sys")

    req = http.requests[0]
    assert req["headers"]["Authorization"] == "Bearer sk-or-test-key"
    assert req["json"]["reasoning"] == {"exclude": True}
    assert req["json"]["temperature"] == 0.15
    assert req["json"]["max_tokens"] == 768


async def test_generate_respects_custom_settings():
    settings = make_settings(
        openrouter_model="google/gemini-2.5-flash",
        openrouter_base_url="https://proxy.example.com/v1/",
        openrouter_temperature=0.5,
        openrouter_max_tokens=1024,
        openrouter_timeout=42,
    )
    client, http = make_client(settings)

    await client.generate("текст", system="sys")

    req = http.requests[0]
    assert req["url"] == "https://proxy.example.com/v1/chat/completions"
    assert req["json"]["model"] == "google/gemini-2.5-flash"
    assert req["json"]["temperature"] == 0.5
    assert req["json"]["max_tokens"] == 1024
    assert req["timeout"] == 42.0


# ── Ошибки конфигурации ───────────────────────────────────────────────────────


def test_missing_api_key_raises_clear_error():
    with pytest.raises(PostprocessError, match="OPENROUTER_API_KEY"):
        OpenRouterClient(Settings(openrouter_api_key=None))


# ── Фабрика провайдеров ───────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_default_client():
    llm_module._default_client = None
    yield
    llm_module._default_client = None


def test_factory_returns_ollama_by_default(monkeypatch):
    monkeypatch.setattr(llm_module, "get_settings", lambda: Settings(llm_provider="ollama"))
    assert isinstance(get_llm_client(), OllamaClient)


def test_factory_returns_openrouter_when_configured(monkeypatch):
    monkeypatch.setattr(
        llm_module,
        "get_settings",
        lambda: Settings(llm_provider="openrouter", openrouter_api_key="sk-or-test"),
    )
    assert isinstance(get_llm_client(), OpenRouterClient)


async def test_postprocess_works_through_llmclient_interface():
    """postprocess_text не знает о провайдере: любой LLMClient подходит."""
    from backend.services.postprocess import postprocess_text

    captured = {}

    class FakeLLM:
        async def generate(self, prompt, *, system):
            captured["system"] = system
            return f"[edited] {prompt}"

    result = await postprocess_text("сырой текст.", llm=FakeLLM())

    assert result == "[edited] сырой текст."
    # Системный промпт пришёл из core/prompts, а не из кода
    assert "редактор транскрибаций" in captured["system"]

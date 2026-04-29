"""
Тесты для services/postprocess.py
"""

import pytest
from unittest.mock import AsyncMock, patch

from exceptions import OllamaUnavailableError, OllamaTimeoutError
from services.postprocess import _split_into_chunks, _strip_thinking


def test_strip_thinking_removes_block():
    text = "<think>some reasoning</think>result text"
    assert _strip_thinking(text) == "result text"


def test_strip_thinking_multiline():
    text = "<think>\nline1\nline2\n</think>answer"
    assert _strip_thinking(text) == "answer"


def test_strip_thinking_no_block():
    text = "plain text"
    assert _strip_thinking(text) == "plain text"


def test_split_into_chunks_short_text():
    text = "Short text."
    chunks = _split_into_chunks(text, max_chars=1000)
    assert chunks == ["Short text."]


def test_split_into_chunks_respects_sentences():
    text = "First sentence. Second sentence. Third sentence."
    chunks = _split_into_chunks(text, max_chars=20)
    assert len(chunks) > 1
    assert all(len(c) <= 30 for c in chunks)  # каждый чанк компактен


@pytest.mark.asyncio
async def test_postprocess_text_ollama_unavailable():
    import httpx
    with patch("services.postprocess._process_chunk", side_effect=httpx.ConnectError("refused")):
        from services.postprocess import postprocess_text
        with pytest.raises(OllamaUnavailableError):
            await postprocess_text("some text")

"""
Тесты сервиса транскрибации с моком модели faster-whisper.

Проверяется: сбор текста из сегментов, прогресс/ETA, передача языка
из конфигурации (WHISPER_LANGUAGE), обработка ошибок.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.exceptions import TranscriptionError
from backend.services.transcription import transcribe_audio


class FakeSegment:
    def __init__(self, text: str, end: float):
        self.text = text
        self.end = end


class FakeInfo:
    duration = 4.0


class FakeModel:
    """Имитирует faster_whisper.WhisperModel.transcribe."""

    def __init__(self):
        self.calls = []

    def transcribe(self, path, **kwargs):
        self.calls.append({"path": path, **kwargs})
        segments = iter([FakeSegment("Привет,", 2.0), FakeSegment("мир", 4.0)])
        return segments, FakeInfo()


@pytest.fixture
def wav(tmp_path) -> Path:
    f = tmp_path / "audio.wav"
    f.write_bytes(b"fake wav")
    return f


async def test_transcribe_joins_segments_and_reports_100(wav):
    model = FakeModel()
    progress_calls = []

    with patch("backend.services.transcription._load_model", return_value=model):
        result = await transcribe_audio(wav, on_progress=lambda pct, eta: progress_calls.append((pct, eta)))

    assert result == "Привет, мир"
    assert progress_calls[-1] == (100.0, 0)


async def test_transcribe_uses_configured_language(wav):
    model = FakeModel()

    with patch("backend.services.transcription._load_model", return_value=model):
        await transcribe_audio(wav)

    assert model.calls[0]["language"] == "ru"  # дефолт из конфигурации


async def test_transcribe_language_override(wav):
    model = FakeModel()

    with patch("backend.services.transcription._load_model", return_value=model), \
         patch("backend.services.transcription.WHISPER_LANGUAGE", "en"):
        await transcribe_audio(wav)

    assert model.calls[0]["language"] == "en"


async def test_transcribe_language_auto_means_autodetect(wav):
    model = FakeModel()

    with patch("backend.services.transcription._load_model", return_value=model), \
         patch("backend.services.transcription.WHISPER_LANGUAGE", "auto"):
        await transcribe_audio(wav)

    assert model.calls[0]["language"] is None


async def test_transcribe_missing_file_raises(tmp_path):
    with pytest.raises(TranscriptionError, match="не найден"):
        await transcribe_audio(tmp_path / "missing.wav")


async def test_transcribe_wraps_model_errors(wav):
    class BrokenModel:
        def transcribe(self, path, **kwargs):
            raise RuntimeError("CTranslate2 boom")

    with patch("backend.services.transcription._load_model", return_value=BrokenModel()):
        with pytest.raises(TranscriptionError, match="Ошибка транскрибации"):
            await transcribe_audio(wav)

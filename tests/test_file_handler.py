"""
Тесты для services/file_handler.py
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.exceptions import FileValidationError, ConversionError
from backend.services.file_handler import validate_file, convert_to_wav


def test_validate_file_unsupported_extension(tmp_path):
    f = tmp_path / "audio.xyz"
    f.write_bytes(b"data")
    with pytest.raises(FileValidationError, match="Неподдерживаемый формат"):
        validate_file(f, "audio.xyz")


def test_validate_file_empty(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"")
    with pytest.raises(FileValidationError, match="пустой"):
        validate_file(f, "audio.mp3")


def test_validate_file_too_large(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"x")
    with patch("backend.services.file_handler.MAX_FILE_SIZE", 0):
        with pytest.raises(FileValidationError, match="слишком большой"):
            validate_file(f, "audio.mp3")


def test_validate_file_ok(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"valid data")
    validate_file(f, "audio.mp3")  # не должно бросить исключение


def test_convert_to_wav_raises_clear_error_when_ffmpeg_missing(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"valid data")

    with patch("backend.services.file_handler.shutil.which", return_value=None):
        with pytest.raises(ConversionError, match="ffmpeg не найден"):
            asyncio.run(convert_to_wav(f))

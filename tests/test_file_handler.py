"""
Тесты для services/file_handler.py
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from exceptions import FileValidationError, ConversionError
from services.file_handler import validate_file


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
    with patch("services.file_handler.MAX_FILE_SIZE", 0):
        with pytest.raises(FileValidationError, match="слишком большой"):
            validate_file(f, "audio.mp3")


def test_validate_file_ok(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"valid data")
    validate_file(f, "audio.mp3")  # не должно бросить исключение

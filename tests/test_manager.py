"""
Тесты для tasks/manager.py
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from exceptions import TaskNotFoundError
from tasks.manager import TaskManager


def make_manager() -> TaskManager:
    return TaskManager()


def test_create_task_returns_id(tmp_path):
    manager = make_manager()
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"x")
    task_id = manager.create_task(f, "audio.mp3")
    assert isinstance(task_id, str)
    assert len(task_id) == 36  # UUID4


def test_get_task_returns_none_for_unknown():
    manager = make_manager()
    assert manager.get_task("nonexistent") is None


def test_require_task_raises_for_unknown():
    manager = make_manager()
    with pytest.raises(TaskNotFoundError):
        manager.require_task("nonexistent")


def test_task_initial_status(tmp_path):
    manager = make_manager()
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"x")
    task_id = manager.create_task(f, "audio.mp3")
    task = manager.get_task(task_id)
    assert task["status"] == "pending"
    assert task["progress"] == 0.0
    assert task["error"] is None

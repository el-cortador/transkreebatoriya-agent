"""
Тесты оркестрации TaskManager.process_task.

Сервисы (validate_file, convert_to_wav, transcribe_audio, postprocess_text)
мокаются — проверяется только оркестрация: статусы, прогресс, ошибки, cleanup.
Поведение закреплено в core/contracts/pipeline_contract.md.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.exceptions import ConversionError
from backend.tasks.manager import TaskManager


@pytest.fixture
def manager() -> TaskManager:
    return TaskManager()


@pytest.fixture
def task_file(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"fake audio")
    return f


def _make_wav(task_file: Path) -> Path:
    wav = task_file.with_suffix(".wav")
    wav.write_bytes(b"fake wav")
    return wav


def _patch_services(convert=None, transcribe=None, postprocess=None):
    return (
        patch("backend.tasks.manager.validate_file"),
        patch("backend.tasks.manager.convert_to_wav", new=convert or AsyncMock()),
        patch("backend.tasks.manager.transcribe_audio", new=transcribe or AsyncMock()),
        patch("backend.tasks.manager.postprocess_text", new=postprocess or AsyncMock()),
    )


# ── Успешные сценарии ─────────────────────────────────────────────────────────


async def test_process_success_with_postprocess(manager, task_file):
    wav = _make_wav(task_file)
    task_id = manager.create_task(task_file, "audio.mp3", run_postprocess=True)

    v, c, t, p = _patch_services(
        convert=AsyncMock(return_value=wav),
        transcribe=AsyncMock(return_value="сырой текст"),
        postprocess=AsyncMock(return_value="обработанный текст"),
    )
    with v, c, t, p:
        await manager.process_task(task_id)

    task = manager.get_task(task_id)
    assert task["status"] == "done"
    assert task["progress"] == 100.0
    assert task["raw_text"] == "сырой текст"
    assert task["processed_text"] == "обработанный текст"
    assert task["error"] is None


async def test_process_success_without_postprocess(manager, task_file):
    wav = _make_wav(task_file)
    task_id = manager.create_task(task_file, "audio.mp3", run_postprocess=False)

    postprocess = AsyncMock()
    v, c, t, p = _patch_services(
        convert=AsyncMock(return_value=wav),
        transcribe=AsyncMock(return_value="сырой текст"),
        postprocess=postprocess,
    )
    with v, c, t, p:
        await manager.process_task(task_id)

    task = manager.get_task(task_id)
    assert task["status"] == "done"
    assert task["processed_text"] == "сырой текст"  # processed == raw
    postprocess.assert_not_called()


# ── Ошибки ────────────────────────────────────────────────────────────────────


async def test_process_conversion_error_marks_task(manager, task_file):
    task_id = manager.create_task(task_file, "audio.mp3")

    v, c, t, p = _patch_services(
        convert=AsyncMock(side_effect=ConversionError("Ошибка конвертации файла (код 1)")),
    )
    with v, c, t, p:
        await manager.process_task(task_id)

    task = manager.get_task(task_id)
    assert task["status"] == "error"
    assert "конвертации" in task["error"]


async def test_process_unexpected_error_marks_task(manager, task_file):
    task_id = manager.create_task(task_file, "audio.mp3")

    v, c, t, p = _patch_services(
        convert=AsyncMock(side_effect=RuntimeError("boom")),
    )
    with v, c, t, p:
        await manager.process_task(task_id)

    task = manager.get_task(task_id)
    assert task["status"] == "error"
    assert "boom" in task["error"]


# ── Cleanup ───────────────────────────────────────────────────────────────────


async def test_process_cleans_temp_files(manager, task_file):
    wav = _make_wav(task_file)
    task_id = manager.create_task(task_file, "audio.mp3")

    v, c, t, p = _patch_services(
        convert=AsyncMock(return_value=wav),
        transcribe=AsyncMock(return_value="текст"),
        postprocess=AsyncMock(return_value="текст"),
    )
    with v, c, t, p:
        await manager.process_task(task_id)

    assert not task_file.exists(), "Исходный файл не удалён"
    assert not wav.exists(), "WAV не удалён"


async def test_process_cleans_temp_files_on_error(manager, task_file):
    wav = _make_wav(task_file)
    task_id = manager.create_task(task_file, "audio.mp3")

    v, c, t, p = _patch_services(
        convert=AsyncMock(return_value=wav),
        transcribe=AsyncMock(side_effect=RuntimeError("whisper упал")),
    )
    with v, c, t, p:
        await manager.process_task(task_id)

    assert not task_file.exists()
    assert not wav.exists()


# ── TTL ───────────────────────────────────────────────────────────────────────


def test_cleanup_expired_removes_old_done_tasks(manager, task_file):
    task_id = manager.create_task(task_file, "audio.mp3")
    task = manager.get_task(task_id)
    task["status"] = "done"
    task["finished_at"] = datetime.now() - timedelta(seconds=manager.ttl_seconds + 1)

    removed = manager.cleanup_expired()

    assert removed == 1
    assert manager.get_task(task_id) is None


def test_cleanup_expired_keeps_recent_and_running(manager, task_file):
    done_id = manager.create_task(task_file, "audio.mp3")
    manager.get_task(done_id)["status"] = "done"
    manager.get_task(done_id)["finished_at"] = datetime.now()

    running_id = manager.create_task(task_file, "audio2.mp3")
    old_running = manager.get_task(running_id)
    old_running["status"] = "transcribing"  # активные задачи не трогаем, даже старые
    old_running["created_at"] = datetime.now() - timedelta(seconds=manager.ttl_seconds + 1)

    removed = manager.cleanup_expired()

    assert removed == 0
    assert manager.get_task(done_id) is not None
    assert manager.get_task(running_id) is not None

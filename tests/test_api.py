"""
Тесты API-слоя (роутеры) через FastAPI TestClient.

Реальный пайплайн не запускается: TaskManager подменяется через
dependency_overrides, тяжёлые сервисы не вызываются.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.tasks.manager import TaskManager, get_task_manager


@pytest.fixture
def manager() -> TaskManager:
    return TaskManager()


@pytest.fixture
def client(manager):
    app.dependency_overrides[get_task_manager] = lambda: manager
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── /api/config ───────────────────────────────────────────────────────────────


def test_config_returns_limits(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert ".mp3" in data["allowed_extensions"]
    assert data["max_file_size_gb"] > 0
    assert data["postprocess_available"] is True


# ── /api/upload ───────────────────────────────────────────────────────────────


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "Неподдерживаемый формат" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/upload",
        files={"file": ("audio.mp3", b"", "audio/mpeg")},
    )
    assert response.status_code == 400
    assert "пустой" in response.json()["detail"]


def test_upload_rejects_oversized_file_streaming(client):
    """Лимит проверяется во время потоковой записи (патчим лимит до 1 байта)."""
    with patch("backend.api.upload.MAX_FILE_SIZE", 1):
        response = client.post(
            "/api/upload",
            files={"file": ("audio.mp3", b"too much data", "audio/mpeg")},
        )
    assert response.status_code == 400
    assert "слишком большой" in response.json()["detail"]


def test_upload_accepts_valid_file(client, manager):
    mock_manager = MagicMock()
    mock_manager.create_task.return_value = "test-task-id"
    mock_manager.process_task = AsyncMock()
    app.dependency_overrides[get_task_manager] = lambda: mock_manager
    try:
        response = client.post(
            "/api/upload",
            files={"file": ("audio.mp3", b"fake audio data", "audio/mpeg")},
            data={"postprocess": "false"},
        )
    finally:
        app.dependency_overrides[get_task_manager] = lambda: manager

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "pending"
    assert data["filename"] == "audio.mp3"


# ── /api/status ───────────────────────────────────────────────────────────────


def test_status_unknown_task_returns_404(client):
    response = client.get("/api/status/does-not-exist")
    assert response.status_code == 404


def test_status_returns_task_fields(client, manager, tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"x")
    task_id = manager.create_task(f, "audio.mp3")

    response = client.get(f"/api/status/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "pending"
    assert data["progress"] == 0.0
    assert data["error"] is None
    assert data["elapsed_seconds"] >= 0


# ── /api/result ───────────────────────────────────────────────────────────────


def _make_done_task(manager: TaskManager, tmp_path: Path) -> str:
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"x")
    task_id = manager.create_task(f, "audio.mp3")
    task = manager.get_task(task_id)
    task["status"] = "done"
    task["raw_text"] = "сырой текст"
    task["processed_text"] = "обработанный текст"
    return task_id


def test_result_not_ready_returns_400(client, manager, tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"x")
    task_id = manager.create_task(f, "audio.mp3")

    response = client.get(f"/api/result/{task_id}")
    assert response.status_code == 400
    assert "ещё не завершена" in response.json()["detail"]


def test_result_returns_texts(client, manager, tmp_path):
    task_id = _make_done_task(manager, tmp_path)

    response = client.get(f"/api/result/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["raw_text"] == "сырой текст"
    assert data["processed_text"] == "обработанный текст"


def test_download_returns_markdown(client, manager, tmp_path):
    task_id = _make_done_task(manager, tmp_path)

    response = client.get(f"/api/download/{task_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "audio_transcription.md" in response.headers["content-disposition"]
    assert response.text == "обработанный текст"

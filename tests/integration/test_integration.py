"""
Интеграционные тесты против живого сервера (end-to-end).

По умолчанию пропускаются. Активация:
    set TRANSKREE_INTEGRATION=1          (Windows)
    export TRANSKREE_INTEGRATION=1       (Linux/macOS)
    uv run pytest -m integration

Требуется: запущенный сервер (порт APP_PORT, дефолт 8001) и тестовые
медиафайлы в директории test_files/ (test.mp3, test.wav, ...).
Постобработка отключается, чтобы тесты не зависели от Ollama.
"""

import os
import time
from pathlib import Path

import httpx
import pytest

BASE_URL = f"http://localhost:{os.getenv('APP_PORT', '8001')}"
TEST_DIR = Path("test_files")
FORMATS = [".mp3", ".mp4", ".wav", ".m4a", ".mkv"]

POLL_INTERVAL_SEC = 10
POLL_TIMEOUT_SEC = 300


def _server_reachable() -> bool:
    try:
        return httpx.get(f"{BASE_URL}/", timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TRANSKREE_INTEGRATION") != "1",
        reason="интеграционные тесты отключены (задайте TRANSKREE_INTEGRATION=1)",
    ),
    pytest.mark.skipif(
        not _server_reachable(),
        reason=f"сервер {BASE_URL} недоступен",
    ),
]


def test_server_serves_ui():
    response = httpx.get(f"{BASE_URL}/", timeout=5)
    assert response.status_code == 200


def test_config_endpoint():
    response = httpx.get(f"{BASE_URL}/api/config", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_extensions"]
    assert data["max_file_size_gb"] > 0


@pytest.mark.parametrize("ext", FORMATS)
def test_upload_and_transcribe(ext):
    test_file = TEST_DIR / f"test{ext}"
    if not test_file.exists():
        pytest.skip(f"Нет тестового файла {test_file}")

    with open(test_file, "rb") as f:
        response = httpx.post(
            f"{BASE_URL}/api/upload",
            files={"file": (test_file.name, f)},
            data={"postprocess": "false"},
            timeout=60,
        )
    assert response.status_code == 200, f"upload: {response.status_code} {response.text}"
    task_id = response.json()["task_id"]

    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    status_data = {}
    while time.monotonic() < deadline:
        status_data = httpx.get(f"{BASE_URL}/api/status/{task_id}", timeout=10).json()
        if status_data["status"] in ("done", "error"):
            break
        time.sleep(POLL_INTERVAL_SEC)

    assert status_data["status"] == "done", f"задача {task_id}: {status_data.get('error')}"

    result = httpx.get(f"{BASE_URL}/api/result/{task_id}", timeout=30)
    assert result.status_code == 200
    assert result.json()["processed_text"].strip(), "Пустой текст транскрибации"

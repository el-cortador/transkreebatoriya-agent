"""
Точка входа FastAPI приложения для транскрибации.
"""

import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Гарантируем, что backend/ в sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from api.upload import router as upload_router
from api.status import router as status_router
from api.result import router as result_router

_access_logger = logging.getLogger("transkreebatoriya.access")

app = FastAPI(
    title="Transkreebatoriya AI Agent",
    description="ИИ-агент для транскрибации медиафайлов с использованием whisper и Ollama",
    version="1.0.0",
)

# Подключаем API роутеры
app.include_router(upload_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(result_router, prefix="/api")

# Статика для frontend
frontend_dir = backend_dir.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# Состояние rate-limiter для /api/status/ поллинга
_STATUS_POLL_INTERVAL = 180  # секунд между записями в лог на один task_id
_status_poll_last: dict[str, float] = {}


@app.middleware("http")
async def _request_logger(request: Request, call_next):
    """
    Логирует HTTP-запросы. Подавляет спам от поллинга /api/status/:
    успешные GET к /api/status/<id> пишутся не чаще раза в 3 минуты на задачу.
    """
    response = await call_next(request)
    path = request.url.path
    method = request.method

    if method == "GET" and path.startswith("/api/status/") and response.status_code == 200:
        task_id = path.rsplit("/", 1)[-1]
        now = time.monotonic()
        if now - _status_poll_last.get(task_id, 0) >= _STATUS_POLL_INTERVAL:
            _status_poll_last[task_id] = now
            _access_logger.info(f'GET {path} 200')
        # иначе — молчим
    else:
        _access_logger.info(f'{method} {path} {response.status_code}')

    return response


@app.get("/")
async def root():
    """Отдаёт главную страницу UI."""
    return FileResponse(frontend_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001, access_log=False)

"""
Точка входа FastAPI приложения для транскрибации.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api.upload import router as upload_router
from backend.api.status import router as status_router
from backend.api.result import router as result_router
from backend.api.config import router as config_router
from backend.config import APP_HOST, APP_PORT
from backend.llm import close_llm_client
from backend.tasks.manager import task_manager

backend_dir = Path(__file__).resolve().parent

_access_logger = logging.getLogger("transkreebatoriya.access")
logger = logging.getLogger(__name__)

# Как часто фоновый cleaner удаляет завершённые задачи по TTL
_TTL_CLEANUP_INTERVAL = 600  # секунд


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Фоновые ресурсы приложения: TTL-cleaner задач и LLM HTTP-клиент."""

    async def _ttl_cleaner():
        while True:
            await asyncio.sleep(_TTL_CLEANUP_INTERVAL)
            try:
                task_manager.cleanup_expired()
            except Exception as e:
                logger.warning(f"[main] Ошибка TTL-cleaner: {e}")

    cleaner = asyncio.create_task(_ttl_cleaner())
    yield
    cleaner.cancel()
    try:
        await cleaner
    except asyncio.CancelledError:
        pass
    await close_llm_client()


app = FastAPI(
    title="Transkreebatoriya AI Agent",
    description="ИИ-агент для транскрибации медиафайлов с использованием whisper и Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

# Подключаем API роутеры
app.include_router(config_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(result_router, prefix="/api")

# Статика для frontend
frontend_dir = backend_dir.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# Состояние rate-limiter для /api/status/ поллинга
_STATUS_POLL_INTERVAL = 180  # секунд между записями в лог на один task_id
_STATUS_POLL_MAX_KEYS = 1000  # защита от бесконечного роста словаря
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
        if len(_status_poll_last) >= _STATUS_POLL_MAX_KEYS:
            _status_poll_last.clear()
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
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, access_log=False)

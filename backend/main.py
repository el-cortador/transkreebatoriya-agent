"""
Точка входа FastAPI приложения для транскрибации.
"""

import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


class _StatusPollFilter(logging.Filter):
    """
    Подавляет спам в консоли от поллинга /api/status/.

    Успешные GET-запросы к /api/status/<id> логируются не чаще одного раза
    в LOG_INTERVAL секунд на задачу. Все остальные запросы проходят без изменений.
    """

    LOG_INTERVAL = 180  # секунд (3 минуты)
    _last: dict[str, float] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn передаёт аргументы как кортеж:
        # (client_addr, method, path, http_version, status_code)
        args = record.args
        if (
            isinstance(args, tuple)
            and len(args) >= 5
            and args[1] == "GET"
            and isinstance(args[2], str)
            and args[2].startswith("/api/status/")
            and args[4] == 200
        ):
            task_id = args[2].rsplit("/", 1)[-1]
            now = time.monotonic()
            if now - self._last.get(task_id, 0) < self.LOG_INTERVAL:
                return False  # подавить запись
            self._last[task_id] = now
        return True


# Вешаем фильтр на логгер доступа uvicorn
logging.getLogger("uvicorn.access").addFilter(_StatusPollFilter())

# Гарантируем, что backend/ в sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from api.upload import router as upload_router
from api.status import router as status_router
from api.result import router as result_router

app = FastAPI(
    title="Transkreebatoriya AI Agent",
    description="ИИ-агент для транскрибации медиафайлов с использованием whisper и Ollama",
    version="1.0.0"
)

# Подключаем API роутеры
app.include_router(upload_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(result_router, prefix="/api")

# Статика для frontend
frontend_dir = backend_dir.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    """Отдаёт главную страницу UI."""
    return FileResponse(frontend_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)

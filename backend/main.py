"""
Точка входа FastAPI приложения для транскрибации.
"""

import sys
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

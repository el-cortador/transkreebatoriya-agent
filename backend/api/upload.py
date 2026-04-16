"""
API роутер для загрузки файлов.
"""

import asyncio
import uuid
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Form, UploadFile, File, HTTPException

from config import TEMP_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from tasks.manager import task_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    postprocess: str = Form("true"),
):
    """
    Загрузка файла для транскрибации.

    postprocess — строка "true"/"false": запускать ли постобработку через Ollama.
    Возвращает task_id для отслеживания статуса.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")

    run_postprocess = postprocess.lower() not in ("false", "0", "no")

    # Ранняя валидация формата до сохранения на диск
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Поддерживаемые: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Уникальное имя файла: <uuid><ext> — исключает коллизии при параллельных загрузках
    safe_name = f"{uuid.uuid4()}{ext}"
    temp_path = TEMP_DIR / safe_name

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ранняя валидация размера
        file_size = temp_path.stat().st_size
        if file_size == 0:
            raise ValueError("Файл пустой")
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024**3):.1f} ГБ")

        # Создаём задачу и запускаем фоновую обработку
        task_id = task_manager.create_task(temp_path, file.filename, run_postprocess=run_postprocess)
        asyncio.create_task(task_manager.process_task(task_id))

        return {
            "task_id": task_id,
            "status": "pending",
            "filename": file.filename,
        }

    except ValueError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка загрузки: {str(e)}")
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")

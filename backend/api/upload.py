"""
API роутер для загрузки файлов.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import logging

from config import TEMP_DIR
from tasks.manager import task_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Загрузка файла для транскрибации.
    
    Возвращает task_id для отслеживания статуса.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")
    
    # Сохраняем во временную директорию
    temp_path = TEMP_DIR / file.filename
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Создаём задачу
        task_id = task_manager.create_task(temp_path, file.filename)
        
        # Запускаем обработку в фоне
        import asyncio
        asyncio.create_task(task_manager.process_task(task_id))
        
        return {
            "task_id": task_id,
            "status": "pending",
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Ошибка загрузки: {str(e)}")
        # Удаляем файл при ошибке
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")

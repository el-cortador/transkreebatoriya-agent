"""
API роутер для загрузки файлов.
"""

import asyncio
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException

from backend.config import TEMP_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from backend.exceptions import FileValidationError
from backend.models import UploadResponse
from backend.tasks.manager import TaskManager, get_task_manager

router = APIRouter()
logger = logging.getLogger(__name__)

# Размер порции при потоковой записи загружаемого файла
_UPLOAD_CHUNK_BYTES = 1024 * 1024  # 1 МиБ

# Реестр фоновых задач обработки — держим ссылки, чтобы задачи не были
# собраны GC и не терялись молча до завершения.
_background_tasks: set[asyncio.Task] = set()


def _spawn_processing(manager: TaskManager, task_id: str) -> None:
    task = asyncio.create_task(manager.process_task(task_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    postprocess: str = Form("true"),
    manager: TaskManager = Depends(get_task_manager),
) -> UploadResponse:
    """
    Загрузка файла для транскрибации.

    postprocess — строка "true"/"false": запускать ли постобработку через Ollama.
    Возвращает task_id для отслеживания статуса.

    Лимит размера проверяется во время потоковой записи: при превышении
    запись прерывается сразу, частичный файл удаляется.
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
        file_size = 0
        with open(temp_path, "wb") as buffer:
            while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise FileValidationError(
                        f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024**3):.1f} ГБ"
                    )
                buffer.write(chunk)

        if file_size == 0:
            raise FileValidationError("Файл пустой")

        task_id = manager.create_task(temp_path, file.filename, run_postprocess=run_postprocess)
        _spawn_processing(manager, task_id)

        return UploadResponse(task_id=task_id, filename=file.filename)

    except FileValidationError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[upload] Ошибка загрузки: {e}")
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {e}")

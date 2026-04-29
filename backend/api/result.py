"""
API роутер для получения результатов транскрибации.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from exceptions import TaskNotFoundError, TaskNotReadyError
from tasks.manager import TaskManager, get_task_manager

router = APIRouter()


@router.get("/result/{task_id}")
async def get_result(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
):
    """Возвращает результат транскрибации."""
    try:
        task = manager.require_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if task["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Задача ещё не завершена. Текущий статус: {task['status']}"
        )

    return {
        "task_id": task["task_id"],
        "raw_text": task["raw_text"],
        "processed_text": task["processed_text"],
    }


@router.get("/download/{task_id}")
async def download_result(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
):
    """Скачивает результат в виде .md файла."""
    try:
        task = manager.require_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if task["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Задача ещё не завершена. Текущий статус: {task['status']}"
        )

    filename = Path(task["filename"]).stem + "_transcription.md"

    return Response(
        content=task["processed_text"],
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

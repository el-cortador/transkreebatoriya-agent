"""
API роутер для проверки статуса задачи.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from backend.exceptions import TaskNotFoundError
from backend.models import TaskStatus
from backend.tasks.manager import TaskManager, get_task_manager

router = APIRouter()


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
) -> TaskStatus:
    """
    Возвращает текущий статус задачи.

    Статусы: pending, transcribing, processing, done, error
    """
    try:
        task = manager.require_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    elapsed = int((datetime.now() - task["created_at"]).total_seconds())

    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=round(task.get("progress", 0.0), 1),
        eta_seconds=task.get("eta_seconds"),
        elapsed_seconds=elapsed,
        stage_message=task.get("stage_message", ""),
        error=task["error"],
    )

"""
API роутер для проверки статуса задачи.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException

from tasks.manager import task_manager

router = APIRouter()


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Возвращает текущий статус задачи.
    
    Статусы: pending, transcribing, processing, done, error
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    elapsed = int((datetime.now() - task["created_at"]).total_seconds())

    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": round(task.get("progress", 0.0), 1),
        "eta_seconds": task.get("eta_seconds"),
        "elapsed_seconds": elapsed,
        "stage_message": task.get("stage_message", ""),
        "error": task["error"],
    }

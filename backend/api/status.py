"""
API роутер для проверки статуса задачи.
"""

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
    
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "error": task["error"]
    }

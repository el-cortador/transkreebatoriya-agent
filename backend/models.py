"""
Pydantic модели для API транскрибации.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UploadResponse(BaseModel):
    """Ответ на загрузку файла."""
    task_id: str
    status: str = "pending"
    filename: str


class TaskStatus(BaseModel):
    """Статус задачи."""
    task_id: str
    status: str  # pending, transcribing, processing, done, error
    progress: Optional[float] = None
    error: Optional[str] = None


class TranscriptionResult(BaseModel):
    """Результат транскрибации."""
    task_id: str
    raw_text: Optional[str] = None
    processed_text: Optional[str] = None
    created_at: Optional[datetime] = None

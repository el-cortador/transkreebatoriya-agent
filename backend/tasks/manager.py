"""
Менеджер задач для управления фоновыми задачами транскрибации.
"""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from config import TEMP_DIR
from services.file_handler import validate_file, convert_to_wav
from services.transcription import transcribe_audio
from services.postprocess import postprocess_text

logger = logging.getLogger(__name__)


class TaskManager:
    """Управление задачами транскрибации."""
    
    def __init__(self):
        self.tasks: Dict[str, dict] = {}
    
    def create_task(self, file_path: Path, filename: str) -> str:
        """
        Создаёт новую задачу.
        
        Args:
            file_path: Путь к загруженному файлу
            filename: Имя файла
            
        Returns:
            task_id
        """
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "filename": filename,
            "file_path": file_path,
            "raw_text": None,
            "processed_text": None,
            "error": None,
            "created_at": datetime.now(),
        }
        return task_id
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """Получить задачу по ID."""
        return self.tasks.get(task_id)
    
    async def process_task(self, task_id: str):
        """
        Запускает полный процесс транскрибации.
        
        Статусы: pending → transcribing → processing → done/error
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Задача {task_id} не найдена")
        
        try:
            # Валидация
            validate_file(task["file_path"], task["filename"])
            
            # Конвертация в WAV
            task["status"] = "transcribing"
            wav_path = await convert_to_wav(task["file_path"])
            
            # Транскрибация
            raw_text = await transcribe_audio(wav_path)
            task["raw_text"] = raw_text
            
            # Постобработка через Ollama
            task["status"] = "processing"
            processed_text = await postprocess_text(raw_text)
            task["processed_text"] = processed_text
            
            # Готово
            task["status"] = "done"
            
        except Exception as e:
            logger.error(f"Ошибка задачи {task_id}: {str(e)}")
            task["status"] = "error"
            task["error"] = str(e)
        
        finally:
            # Очистка временных файлов
            await self._cleanup_temp_files(task_id)
    
    async def _cleanup_temp_files(self, task_id: str):
        """Удаляет временные файлы задачи."""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        # Удаляем исходный файл, WAV, txt
        for path_key in ["file_path"]:
            path = task.get(path_key)
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                except Exception as e:
                    logger.warning(f"Не удалось удалить {path}: {e}")
        
        # Удаляем сопутствующие файлы (.wav, .txt)
        base_path = Path(task["file_path"])
        for suffix in [".wav", ".txt"]:
            temp_file = base_path.with_suffix(suffix)
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass


# Глобальный экземпляр
task_manager = TaskManager()

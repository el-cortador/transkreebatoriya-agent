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

    def create_task(self, file_path: Path, filename: str, run_postprocess: bool = True) -> str:
        """
        Создаёт новую задачу.

        Args:
            file_path:       Путь к загруженному файлу.
            filename:        Оригинальное имя файла.
            run_postprocess: Запускать ли постобработку через Ollama.

        Returns:
            task_id
        """
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "filename": filename,
            "file_path": file_path,
            "run_postprocess": run_postprocess,
            "raw_text": None,
            "processed_text": None,
            "error": None,
            "created_at": datetime.now(),
            # Прогресс
            "progress": 0.0,
            "eta_seconds": None,
            "stage_message": "В очереди...",
        }
        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        """Получить задачу по ID."""
        return self.tasks.get(task_id)

    async def process_task(self, task_id: str):
        """
        Запускает полный процесс транскрибации.

        Статусы: pending → transcribing → processing → done/error
        Прогресс:
          - Без постобработки: конвертация 0–5%, транскрибация 5–100%
          - С постобработкой:  конвертация 0–5%, транскрибация 5–75%, постобработка 75–100%
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Задача {task_id} не найдена")

        run_postprocess: bool = task.get("run_postprocess", True)

        try:
            # Валидация
            validate_file(task["file_path"], task["filename"])

            # ── Стадия 1: конвертация ────────────────────────────────────────
            task["status"] = "transcribing"
            task["stage_message"] = "Конвертация аудио..."
            task["progress"] = 1.0
            wav_path = await convert_to_wav(task["file_path"])
            task["progress"] = 5.0

            # ── Стадия 2: транскрибация ──────────────────────────────────────
            task["stage_message"] = "Транскрибация речи..."

            if run_postprocess:
                # транскрибация занимает 5→75%, постобработка 75→100%
                def _on_transcription(pct: float, eta: Optional[int]):
                    task["progress"] = 5.0 + pct * 0.70
                    task["eta_seconds"] = eta
            else:
                # транскрибация занимает всё оставшееся 5→100%
                def _on_transcription(pct: float, eta: Optional[int]):
                    task["progress"] = 5.0 + pct * 0.95
                    task["eta_seconds"] = eta

            raw_text = await transcribe_audio(wav_path, on_progress=_on_transcription)
            task["raw_text"] = raw_text

            # ── Стадия 3: постобработка (только если включена) ───────────────
            if run_postprocess and raw_text.strip():
                task["progress"] = 75.0
                task["eta_seconds"] = None
                task["status"] = "processing"
                task["stage_message"] = "Постобработка через Ollama..."

                def _on_postprocess(pct: float, eta: Optional[int]):
                    task["progress"] = 75.0 + pct * 0.25
                    if eta is not None:
                        task["eta_seconds"] = eta

                processed_text = await postprocess_text(raw_text, on_progress=_on_postprocess)
                task["processed_text"] = processed_text
            else:
                # Постобработка отключена — возвращаем сырой текст whisper
                task["processed_text"] = raw_text

            task["status"] = "done"
            task["progress"] = 100.0
            task["stage_message"] = "Готово"
            task["eta_seconds"] = 0

        except Exception as e:
            logger.error(f"Ошибка задачи {task_id}: {str(e)}")
            task["status"] = "error"
            task["error"] = str(e)

        finally:
            await self._cleanup_temp_files(task_id)

    async def _cleanup_temp_files(self, task_id: str):
        """Удаляет временные файлы задачи."""
        task = self.tasks.get(task_id)
        if not task:
            return

        for path_key in ["file_path"]:
            path = task.get(path_key)
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                except Exception as e:
                    logger.warning(f"Не удалось удалить {path}: {e}")

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

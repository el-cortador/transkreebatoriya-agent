"""
API роутер публичной конфигурации сервера.

Единый источник правды о лимитах для клиентов: UI читает этот эндпоинт
при загрузке страницы вместо захардкоженных значений.
"""

from fastapi import APIRouter

from backend.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_GB
from backend.models import AppConfig

router = APIRouter()


@router.get("/config", response_model=AppConfig)
async def get_config() -> AppConfig:
    """Возвращает публичные лимиты и настройки сервера."""
    return AppConfig(
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
        max_file_size_gb=MAX_FILE_SIZE_GB,
        postprocess_available=True,
    )

"""
Настройки приложения на pydantic-settings.

Значения читаются из .env (если он есть), затем из переменных окружения.
В отличие от старого config.py, значения валидируются при старте:
некорректная конфигурация падает с понятной ошибкой, а не в середине задачи.

Для обратной совместимости модульные константы доступны через backend/config.py.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Whisper ───────────────────────────────────────────────────────────
    # Варианты модели: tiny | base | small | medium | large-v3
    # Чем больше модель — тем точнее, но медленнее.
    whisper_model_name: Literal["tiny", "base", "small", "medium", "large-v3"] = "base"

    # "auto" → CUDA если доступно, иначе CPU. Принудительно: "cpu" или "cuda".
    whisper_device: Literal["auto", "cpu", "cuda"] = "auto"

    # Язык распознавания (ISO-639-1). None/"auto" → автоопределение whisper.
    whisper_language: str = "ru"

    # ── ffmpeg ────────────────────────────────────────────────────────────
    ffmpeg_path: str = "ffmpeg"

    # ── Ollama ────────────────────────────────────────────────────────────
    ollama_api_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "qwen2.5:1.5b"

    # Runtime options для Ollama / llama.cpp backend.
    ollama_keep_alive: str = "15m"
    ollama_num_ctx: int = Field(default=2048, gt=0)
    ollama_num_predict: int = Field(default=768, gt=0)
    ollama_temperature: float = Field(default=0.15, ge=0.0)
    ollama_top_p: float = Field(default=0.9, gt=0.0, le=1.0)
    ollama_top_k: int = Field(default=30, ge=0)
    ollama_min_p: float = Field(default=0.05, ge=0.0, le=1.0)
    ollama_repeat_last_n: int = 128
    ollama_repeat_penalty: float = 1.08

    # Таймаут одного запроса к Ollama в секундах (на один чанк).
    ollama_timeout: int = Field(default=1800, gt=0)

    # ── Постобработка ─────────────────────────────────────────────────────
    # Максимум символов в одном чанке постобработки.
    postprocess_chunk_chars: int = Field(default=1800, ge=200)

    # Сколько чанков обрабатывать параллельно (требует OLLAMA_NUM_PARALLEL в окружении).
    postprocess_concurrency: int = Field(default=1, ge=1)

    # ── Лимиты файлов ─────────────────────────────────────────────────────
    max_file_size_gb: int = Field(default=6, gt=0)

    # ── Задачи ────────────────────────────────────────────────────────────
    # Сколько часов хранить завершённые (done/error) задачи в памяти.
    task_ttl_hours: float = Field(default=24.0, gt=0)

    # ── Сервер ────────────────────────────────────────────────────────────
    app_host: str = "localhost"
    app_port: int = Field(default=8001, gt=0, le=65535)

    # ── Hugging Face (опционально) ────────────────────────────────────────
    hf_token: Optional[str] = None

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_gb * 1024 * 1024 * 1024

    @property
    def task_ttl_seconds(self) -> float:
        return self.task_ttl_hours * 3600


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Глобальный экземпляр настроек (создаётся один раз)."""
    return Settings()

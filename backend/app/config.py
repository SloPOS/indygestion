from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Indygestion Backend"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api/v1"

    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    database_url: str = "postgresql+asyncpg://indygestion:indygestion@localhost:5432/indygestion"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    media_root: str = "/media/indygestion"
    storage_active_path: str = "/media/indygestion/projects"
    storage_archive_path: str = "/media/indygestion/archive"
    storage_staging_path: str = "/media/indygestion/staging"
    storage_review_path: str = "/media/indygestion/_review"

    reversible_window_hours: int = 24


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

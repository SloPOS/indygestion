from datetime import datetime
from typing import Any

from pydantic import BaseModel


DEFAULT_SETTINGS: dict[str, tuple[str, Any]] = {
    "network_speed": ("str", "10GbE"),
    "upload_chunk_size_mb": ("int", 100),
    "max_concurrent_uploads": ("int", 4),
    "whisper_model": ("str", "small"),
    "similarity_threshold": ("float", 0.75),
    "cross_session_window_days": ("int", 30),
    "default_archive_preset": ("str", "h265_crf18"),
    "auto_ingest_enabled": ("bool", False),
    "video_extensions": ("str", ".mov,.mp4,.mxf,.avi,.braw"),
    "min_file_size_mb": ("int", 10),
    "storage_active": ("str", "/media/indygestion/projects"),
    "storage_archive": ("str", "/media/indygestion/archive"),
    "storage_staging": ("str", "/media/indygestion/staging"),
}


class SettingResponse(BaseModel):
    key: str
    value_type: str
    value: Any
    updated_at: datetime


class SettingUpsert(BaseModel):
    key: str
    value: Any
    value_type: str | None = None


class AppSettingsResponse(BaseModel):
    settings: list[SettingResponse]

from datetime import datetime

from pydantic import BaseModel

from app.models.clip import ClipIngestStatus, ClipSource, ProxyStatus


class ClipCreate(BaseModel):
    filename: str
    original_path: str
    file_size: int = 0
    source: ClipSource = ClipSource.web_upload
    source_device: str | None = None
    ingest_session_id: int | None = None


class ClipUpdate(BaseModel):
    project_id: int | None = None
    ingest_status: ClipIngestStatus | None = None
    transcript_text: str | None = None
    transcript_json_path: str | None = None
    proxy_path: str | None = None
    proxy_status: ProxyStatus | None = None
    similarity_matches: dict | None = None


class ClipReassign(BaseModel):
    project_id: int | None = None


class SimilaritySuggestion(BaseModel):
    clip_id: int
    project_id: int | None
    score: float
    transcript_snippet: str | None


class SimilarityResponse(BaseModel):
    suggestions: list[SimilaritySuggestion]


class ClipResponse(BaseModel):
    id: int
    project_id: int | None
    ingest_session_id: int | None
    filename: str
    original_path: str
    file_size: int
    duration: float | None
    resolution: str | None
    codec: str | None
    fps: float | None
    bitrate: int | None
    proxy_path: str | None
    proxy_status: ProxyStatus
    transcript_text: str | None
    transcript_json_path: str | None
    checksum_sha256: str | None
    source: ClipSource
    source_device: str | None
    ingest_status: ClipIngestStatus
    similarity_matches: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClipListResponse(BaseModel):
    items: list[ClipResponse]
    total: int
    offset: int
    limit: int

from datetime import datetime

from pydantic import BaseModel

from app.models.ingest_session import IngestSessionStatus, IngestSource


class IngestSessionCreate(BaseModel):
    source: IngestSource
    device_info: dict | None = None


class IngestSessionUpdate(BaseModel):
    status: IngestSessionStatus | None = None
    clip_count: int | None = None
    total_size: int | None = None
    completed_at: datetime | None = None


class IngestSessionResponse(BaseModel):
    id: int
    source: IngestSource
    device_info: dict | None
    clip_count: int
    total_size: int
    status: IngestSessionStatus
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class IngestSessionListResponse(BaseModel):
    items: list[IngestSessionResponse]
    total: int
    offset: int
    limit: int

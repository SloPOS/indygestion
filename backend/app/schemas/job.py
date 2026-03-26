from datetime import datetime

from pydantic import BaseModel

from app.models.ingest_job import JobStatus, JobType


class JobCreate(BaseModel):
    clip_id: int | None = None
    project_id: int | None = None
    job_type: JobType


class JobUpdate(BaseModel):
    status: JobStatus | None = None
    progress: float | None = None
    error_message: str | None = None


class JobResponse(BaseModel):
    id: int
    clip_id: int | None
    project_id: int | None
    job_type: JobType
    status: JobStatus
    progress: float
    error_message: str | None
    worker_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    offset: int
    limit: int

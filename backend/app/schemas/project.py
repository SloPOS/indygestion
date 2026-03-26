from datetime import datetime

from pydantic import BaseModel, Field

from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProjectCreate(ProjectBase):
    folder_path: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    tags: list[str] | None = None
    notes: str | None = None
    archive_preset: dict | None = None
    estimated_archive_size: float | None = None
    folder_path: str | None = None
    archive_path: str | None = None


class ProjectResponse(ProjectBase):
    id: int
    status: ProjectStatus
    folder_path: str | None = None
    archive_path: str | None = None
    archive_preset: dict | None = None
    estimated_archive_size: float | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    offset: int
    limit: int

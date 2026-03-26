from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ingest_job import IngestJob, JobType
from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.tasks.celery_app import archive_project

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(Project.id)))
    items = (await db.scalars(select(Project).order_by(Project.created_at.desc()).offset(offset).limit(limit))).all()
    return ProjectListResponse(items=items, total=total or 0, offset=offset, limit=limit)


@router.post("", response_model=ProjectResponse)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(project, k, v)

    if project.status == ProjectStatus.archived and project.archived_at is None:
        project.archived_at = datetime.utcnow()

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return {"ok": True}


@router.post("/{project_id}/finish", response_model=ProjectResponse)
async def finish_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = ProjectStatus.finished
    await db.commit()
    await db.refresh(project)
    return project


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def trigger_archive(project_id: int, preset: str = "h265_crf18", db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectStatus.archiving
    db.add(IngestJob(project_id=project.id, job_type=JobType.archive))
    await db.commit()
    await db.refresh(project)

    archive_project.delay(project.id, preset)
    return project

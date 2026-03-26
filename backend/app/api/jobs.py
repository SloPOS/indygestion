from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ingest_job import IngestJob, JobStatus
from app.schemas.job import JobListResponse, JobResponse
from app.tasks.celery_app import archive_project, embed_clip, generate_proxy, transcribe_clip

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    status: JobStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IngestJob)
    count_stmt = select(func.count(IngestJob.id))
    if status:
        stmt = stmt.where(IngestJob.status == status)
        count_stmt = count_stmt.where(IngestJob.status == status)

    total = await db.scalar(count_stmt)
    items = (await db.scalars(stmt.order_by(IngestJob.created_at.desc()).offset(offset).limit(limit))).all()
    return JobListResponse(items=items, total=total or 0, offset=offset, limit=limit)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.queued
    job.progress = 0
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    await db.commit()
    await db.refresh(job)

    if job.job_type.value == "transcribe" and job.clip_id:
        transcribe_clip.delay(job.clip_id)
    elif job.job_type.value == "proxy" and job.clip_id:
        generate_proxy.delay(job.clip_id)
    elif job.job_type.value == "embed" and job.clip_id:
        embed_clip.delay(job.clip_id)
    elif job.job_type.value == "archive" and job.project_id:
        archive_project.delay(job.project_id, "h265_crf18")

    return job


@router.patch("/{job_id}/status", response_model=JobResponse)
async def update_job_status(job_id: int, status: JobStatus, progress: float = 0, db: AsyncSession = Depends(get_db)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = status
    job.progress = progress
    if status == JobStatus.running and job.started_at is None:
        job.started_at = datetime.utcnow()
    if status in {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}:
        job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job

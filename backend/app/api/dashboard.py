from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.clip import Clip
from app.models.ingest_job import IngestJob, JobStatus
from app.models.ingest_session import IngestSession
from app.models.project import Project, ProjectStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _dir_size(path: str) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


@router.get("/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    storage = {
        "projects_bytes": _dir_size(settings.storage_active_path),
        "archive_bytes": _dir_size(settings.storage_archive_path),
        "staging_bytes": _dir_size(settings.storage_staging_path),
    }

    active_jobs = (
        await db.scalars(select(IngestJob).where(IngestJob.status.in_([JobStatus.queued, JobStatus.running])))
    ).all()
    recent_ingests = (
        await db.scalars(select(IngestSession).order_by(IngestSession.started_at.desc()).limit(10))
    ).all()

    status_counts_rows = (
        await db.execute(select(Project.status, func.count(Project.id)).group_by(Project.status))
    ).all()
    project_counts = {status.value if isinstance(status, ProjectStatus) else str(status): count for status, count in status_counts_rows}

    total_clips = await db.scalar(select(func.count(Clip.id)))
    total_projects = await db.scalar(select(func.count(Project.id)))

    return {
        "storage": storage,
        "queue": {
            "active_count": len(active_jobs),
            "items": [
                {
                    "id": j.id,
                    "type": j.job_type,
                    "status": j.status,
                    "progress": j.progress,
                    "clip_id": j.clip_id,
                    "project_id": j.project_id,
                }
                for j in active_jobs
            ],
        },
        "recent_ingests": [
            {
                "id": s.id,
                "source": s.source,
                "status": s.status,
                "clip_count": s.clip_count,
                "total_size": s.total_size,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
            }
            for s in recent_ingests
        ],
        "project_counts_by_status": project_counts,
        "totals": {
            "clips": total_clips or 0,
            "projects": total_projects or 0,
        },
    }

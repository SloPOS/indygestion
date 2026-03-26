from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

LOGGER = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://indygestion:indygestion@postgres:5432/indygestion")
if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)

ENGINE = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)


@contextmanager
def db_session() -> Session:
    session = Session(ENGINE)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def update_ingest_job(
    session: Session,
    *,
    clip_id: int | None,
    project_id: int | None,
    job_type: str,
    status: str,
    progress: float,
    worker_id: str | None,
    error_message: str | None = None,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO ingest_jobs (clip_id, project_id, job_type, status, progress, worker_id, error_message, started_at, created_at)
            VALUES (:clip_id, :project_id, :job_type, :status, :progress, :worker_id, :error_message,
                    CASE WHEN :status='running' THEN NOW() ELSE NULL END,
                    NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "clip_id": clip_id,
            "project_id": project_id,
            "job_type": job_type,
            "status": status,
            "progress": progress,
            "worker_id": worker_id,
            "error_message": error_message,
        },
    )

    session.execute(
        text(
            """
            UPDATE ingest_jobs
            SET status=:status,
                progress=:progress,
                error_message=:error_message,
                worker_id=:worker_id,
                started_at = COALESCE(started_at, CASE WHEN :status='running' THEN NOW() ELSE started_at END),
                completed_at = CASE WHEN :status IN ('completed','failed','cancelled') THEN NOW() ELSE completed_at END
            WHERE id = (
                SELECT id FROM ingest_jobs
                WHERE (:clip_id IS NULL OR clip_id=:clip_id)
                  AND (:project_id IS NULL OR project_id=:project_id)
                  AND job_type=:job_type
                ORDER BY created_at DESC
                LIMIT 1
            )
            """
        ),
        {
            "clip_id": clip_id,
            "project_id": project_id,
            "job_type": job_type,
            "status": status,
            "progress": progress,
            "error_message": error_message,
            "worker_id": worker_id,
        },
    )

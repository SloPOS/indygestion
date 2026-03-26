from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ingest_session import IngestSession, IngestSessionStatus
from app.schemas.ingest import (
    IngestSessionCreate,
    IngestSessionListResponse,
    IngestSessionResponse,
    IngestSessionUpdate,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/sessions", response_model=IngestSessionListResponse)
async def list_sessions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(IngestSession.id)))
    items = (
        await db.scalars(select(IngestSession).order_by(IngestSession.started_at.desc()).offset(offset).limit(limit))
    ).all()
    return IngestSessionListResponse(items=items, total=total or 0, offset=offset, limit=limit)


@router.post("/sessions", response_model=IngestSessionResponse)
async def create_session(payload: IngestSessionCreate, db: AsyncSession = Depends(get_db)):
    session = IngestSession(**payload.model_dump())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=IngestSessionResponse)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(IngestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Ingest session not found")
    return session


@router.patch("/sessions/{session_id}", response_model=IngestSessionResponse)
async def update_session(session_id: int, payload: IngestSessionUpdate, db: AsyncSession = Depends(get_db)):
    session = await db.get(IngestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Ingest session not found")

    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(session, k, v)

    if session.status == IngestSessionStatus.complete and session.completed_at is None:
        session.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)
    return session

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.clip import Clip
from app.schemas.clip import (
    ClipCreate,
    ClipListResponse,
    ClipReassign,
    ClipResponse,
    ClipUpdate,
    SimilarityResponse,
)
from app.services.clustering import suggest_similar_clips

router = APIRouter(prefix="/clips", tags=["clips"])


@router.get("", response_model=ClipListResponse)
async def list_clips(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(Clip.id)))
    items = (await db.scalars(select(Clip).order_by(Clip.created_at.desc()).offset(offset).limit(limit))).all()
    return ClipListResponse(items=items, total=total or 0, offset=offset, limit=limit)


@router.post("", response_model=ClipResponse)
async def create_clip(payload: ClipCreate, db: AsyncSession = Depends(get_db)):
    clip = Clip(**payload.model_dump())
    db.add(clip)
    await db.commit()
    await db.refresh(clip)
    return clip


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: int, db: AsyncSession = Depends(get_db)):
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return clip


@router.patch("/{clip_id}", response_model=ClipResponse)
async def update_clip(clip_id: int, payload: ClipUpdate, db: AsyncSession = Depends(get_db)):
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(clip, k, v)

    await db.commit()
    await db.refresh(clip)
    return clip


@router.delete("/{clip_id}")
async def delete_clip(clip_id: int, db: AsyncSession = Depends(get_db)):
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    await db.delete(clip)
    await db.commit()
    return {"ok": True}


@router.post("/{clip_id}/reassign", response_model=ClipResponse)
async def reassign_clip(clip_id: int, payload: ClipReassign, db: AsyncSession = Depends(get_db)):
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    clip.project_id = payload.project_id
    await db.commit()
    await db.refresh(clip)
    return clip


@router.get("/{clip_id}/similarity", response_model=SimilarityResponse)
async def similarity_search(
    clip_id: int,
    threshold: float = Query(default=0.75, ge=0.0, le=1.0),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    clip = await db.get(Clip, clip_id)
    if not clip or clip.embedding is None:
        raise HTTPException(status_code=404, detail="Clip or embedding not found")

    suggestions = await suggest_similar_clips(db, clip.embedding, limit=limit + 1, threshold=threshold)
    filtered = [s for s in suggestions if s["clip_id"] != clip_id][:limit]
    return SimilarityResponse(suggestions=filtered)

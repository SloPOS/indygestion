from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.clip import Clip


async def suggest_similar_clips(
    db: AsyncSession,
    embedding: list[float],
    limit: int = 10,
    threshold: float = 0.75,
) -> list[dict]:
    distance = Clip.embedding.cosine_distance(embedding).label("distance")
    stmt = (
        select(Clip, distance)
        .where(and_(Clip.embedding.is_not(None), Clip.id.is_not(None)))
        .options(joinedload(Clip.project))
        .order_by(distance.asc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    suggestions = []
    for clip, dist in rows:
        score = 1 - float(dist)
        if score < threshold:
            continue
        suggestions.append(
            {
                "clip_id": clip.id,
                "project_id": clip.project_id,
                "score": round(score, 4),
                "transcript_snippet": (clip.transcript_text or "")[:240] or None,
            }
        )
    return suggestions

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
from celery import shared_task
from sqlalchemy import text

from tasks import db_session

LOGGER = logging.getLogger(__name__)
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
AUTO_ASSIGN_ENABLED = os.getenv("AUTO_ASSIGN_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
CROSS_SESSION_DAYS = int(os.getenv("CROSS_SESSION_WINDOW_DAYS", "30"))


@dataclass
class Match:
    kind: str
    target_id: int
    score: float


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _to_np(embedding_value) -> np.ndarray:
    if isinstance(embedding_value, str):
        cleaned = embedding_value.strip("[]")
        vals = [float(v) for v in cleaned.split(",") if v.strip()]
        return np.array(vals, dtype=np.float32)
    if isinstance(embedding_value, (list, tuple)):
        return np.array(embedding_value, dtype=np.float32)
    raise ValueError("Unsupported embedding format")


@shared_task(bind=True, name="tasks.cluster.cluster_clip")
def cluster_clip(self, clip_id: int) -> dict:
    self.update_state(state="PROGRESS", meta={"progress": 5, "stage": "loading_embedding"})

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=CROSS_SESSION_DAYS)

    with db_session() as session:
        clip = session.execute(
            text("SELECT id, project_id, embedding FROM clips WHERE id=:clip_id"), {"clip_id": clip_id}
        ).mappings().first()
        if not clip or clip.get("embedding") is None:
            raise ValueError(f"Clip {clip_id} has no embedding")

        target_embedding = _to_np(clip["embedding"])

        self.update_state(state="PROGRESS", meta={"progress": 30, "stage": "similarity_unassigned"})
        unassigned = session.execute(
            text(
                """
                SELECT id, embedding
                FROM clips
                WHERE id != :clip_id
                  AND project_id IS NULL
                  AND embedding IS NOT NULL
                  AND created_at >= :window_start
                """
            ),
            {"clip_id": clip_id, "window_start": window_start},
        ).mappings().all()

        clip_matches: list[Match] = []
        for row in unassigned:
            score = _cosine(target_embedding, _to_np(row["embedding"]))
            clip_matches.append(Match(kind="clip", target_id=row["id"], score=score))

        self.update_state(state="PROGRESS", meta={"progress": 60, "stage": "similarity_projects"})
        project_embedding_rows = session.execute(
            text(
                """
                SELECT c.project_id, c.embedding
                FROM clips c
                WHERE c.project_id IS NOT NULL
                  AND c.embedding IS NOT NULL
                """
            )
        ).mappings().all()

        grouped: dict[int, list[np.ndarray]] = {}
        for row in project_embedding_rows:
            try:
                grouped.setdefault(row["project_id"], []).append(_to_np(row["embedding"]))
            except Exception:
                continue

        project_matches: list[Match] = []
        for project_id, vectors in grouped.items():
            if not vectors:
                continue
            centroid = np.mean(np.stack(vectors), axis=0)
            score = _cosine(target_embedding, centroid)
            project_matches.append(Match(kind="project", target_id=project_id, score=score))

        ranked = sorted([*clip_matches, *project_matches], key=lambda m: m.score, reverse=True)
        suggestions = [
            {"type": m.kind, "id": m.target_id, "score": round(m.score, 6)}
            for m in ranked[:20]
            if m.score > 0
        ]

        top_project = next((m for m in ranked if m.kind == "project"), None)

        assign_project_id = None
        ingest_status = "reviewing"
        if AUTO_ASSIGN_ENABLED and top_project and top_project.score >= SIMILARITY_THRESHOLD:
            assign_project_id = top_project.target_id
            ingest_status = "assigned"

        session.execute(
            text(
                """
                UPDATE clips
                SET similarity_matches=:suggestions::jsonb,
                    project_id=COALESCE(:assign_project_id, project_id),
                    ingest_status=:ingest_status,
                    updated_at=NOW()
                WHERE id=:clip_id
                """
            ),
            {
                "suggestions": json.dumps(suggestions),
                "assign_project_id": assign_project_id,
                "ingest_status": ingest_status,
                "clip_id": clip_id,
            },
        )

    self.update_state(state="PROGRESS", meta={"progress": 100, "stage": "completed"})
    return {
        "clip_id": clip_id,
        "suggestions": suggestions,
        "assigned_project_id": assign_project_id,
        "auto_assign": AUTO_ASSIGN_ENABLED,
    }

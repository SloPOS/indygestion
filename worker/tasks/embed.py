from __future__ import annotations

import logging
import os

import requests
from celery import shared_task
from sqlalchemy import text

from tasks import db_session, update_ingest_job

LOGGER = logging.getLogger(__name__)
WHISPER_SERVICE_URL = os.getenv("WHISPER_SERVICE_URL", "http://whisper:9000")


@shared_task(bind=True, name="tasks.embed.embed_clip", autoretry_for=(requests.RequestException,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def embed_clip(self, clip_id: int, trigger_next: bool = True) -> dict:
    worker_id = self.request.hostname
    self.update_state(state="PROGRESS", meta={"progress": 5, "stage": "loading_transcript"})

    with db_session() as session:
        clip = session.execute(
            text("SELECT id, project_id, transcript_text FROM clips WHERE id=:clip_id"), {"clip_id": clip_id}
        ).mappings().first()
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")
        transcript_text = (clip.get("transcript_text") or "").strip()
        if not transcript_text:
            raise ValueError(f"Clip {clip_id} has no transcript text")

        update_ingest_job(
            session,
            clip_id=clip_id,
            project_id=clip["project_id"],
            job_type="embed",
            status="running",
            progress=10,
            worker_id=worker_id,
        )

    self.update_state(state="PROGRESS", meta={"progress": 40, "stage": "embedding"})
    response = requests.post(
        f"{WHISPER_SERVICE_URL}/embed",
        json={"text": transcript_text},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    embedding = payload.get("embedding", [])
    model = payload.get("model")

    if not isinstance(embedding, list) or len(embedding) != 384:
        raise ValueError(f"Expected 384-dim embedding, got {len(embedding) if isinstance(embedding, list) else 'invalid'}")

    with db_session() as session:
        session.execute(
            text("UPDATE clips SET embedding=:embedding::vector, updated_at=NOW() WHERE id=:clip_id"),
            {"embedding": str(embedding), "clip_id": clip_id},
        )
        update_ingest_job(
            session,
            clip_id=clip_id,
            project_id=None,
            job_type="embed",
            status="completed",
            progress=100,
            worker_id=worker_id,
        )

    if trigger_next:
        from tasks.cluster import cluster_clip

        cluster_clip.delay(clip_id)

    self.update_state(state="PROGRESS", meta={"progress": 100, "stage": "completed"})
    return {"clip_id": clip_id, "embedding_dim": len(embedding), "model": model}

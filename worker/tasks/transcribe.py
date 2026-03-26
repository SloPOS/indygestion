from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests
from celery import shared_task
from sqlalchemy import text

from tasks import db_session, update_ingest_job

LOGGER = logging.getLogger(__name__)
WHISPER_SERVICE_URL = os.getenv("WHISPER_SERVICE_URL", "http://whisper:9000")
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/media/indygestion"))


@shared_task(bind=True, name="tasks.transcribe.transcribe_clip", autoretry_for=(requests.RequestException,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def transcribe_clip(self, clip_id: int, trigger_next: bool = True) -> dict:
    worker_id = self.request.hostname
    self.update_state(state="PROGRESS", meta={"progress": 5, "stage": "loading_clip"})

    with db_session() as session:
        clip = session.execute(
            text("SELECT id, original_path, project_id FROM clips WHERE id=:clip_id"), {"clip_id": clip_id}
        ).mappings().first()
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")

        source_path = Path(clip["original_path"])
        if not source_path.exists():
            raise FileNotFoundError(f"Source file missing: {source_path}")

        session.execute(
            text("UPDATE clips SET ingest_status='transcribing', updated_at=NOW() WHERE id=:clip_id"), {"clip_id": clip_id}
        )
        update_ingest_job(
            session,
            clip_id=clip_id,
            project_id=clip["project_id"],
            job_type="transcribe",
            status="running",
            progress=10,
            worker_id=worker_id,
        )

    self.update_state(state="PROGRESS", meta={"progress": 30, "stage": "whisper_request"})
    response = requests.post(
        f"{WHISPER_SERVICE_URL}/transcribe",
        json={"file_path": str(source_path)},
        timeout=60 * 60,
    )
    response.raise_for_status()
    payload = response.json()

    segments = payload.get("segments", [])
    full_text = payload.get("full_text", "").strip()
    language = payload.get("language", "unknown")

    transcript_dir = source_path.parent.parent / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_json_path = transcript_dir / f"{source_path.stem}.json"
    transcript_txt_path = transcript_dir / f"{source_path.stem}.txt"

    transcript_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    transcript_txt_path.write_text(full_text, encoding="utf-8")

    with db_session() as session:
        session.execute(
            text(
                """
                UPDATE clips
                SET transcript_text=:transcript_text,
                    transcript_json_path=:transcript_json_path,
                    ingest_status='reviewing',
                    updated_at=NOW()
                WHERE id=:clip_id
                """
            ),
            {
                "transcript_text": full_text,
                "transcript_json_path": str(transcript_json_path),
                "clip_id": clip_id,
            },
        )
        update_ingest_job(
            session,
            clip_id=clip_id,
            project_id=None,
            job_type="transcribe",
            status="completed",
            progress=100,
            worker_id=worker_id,
        )

    if trigger_next:
        from tasks.embed import embed_clip

        embed_clip.delay(clip_id, True)

    self.update_state(state="PROGRESS", meta={"progress": 100, "stage": "completed"})
    return {
        "clip_id": clip_id,
        "segments": len(segments),
        "language": language,
        "transcript_json_path": str(transcript_json_path),
        "transcript_txt_path": str(transcript_txt_path),
    }

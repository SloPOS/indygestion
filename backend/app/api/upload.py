import base64
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.clip import Clip, ClipIngestStatus, ClipSource
from app.models.ingest_job import IngestJob, JobType
from app.services.ffprobe import probe_video
from app.tasks.celery_app import generate_proxy, transcribe_clip

router = APIRouter(prefix="/upload", tags=["upload"])


class TusHookEvent(BaseModel):
    Type: str
    Event: dict


def _decode_tus_metadata(metadata_header: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not metadata_header:
        return out
    for chunk in metadata_header.split(","):
        parts = chunk.strip().split(" ")
        if len(parts) != 2:
            continue
        key, raw_val = parts
        try:
            out[key] = base64.b64decode(raw_val).decode("utf-8")
        except Exception:
            out[key] = raw_val
    return out


@router.post("/tusd/on-complete")
async def tusd_on_complete(payload: TusHookEvent, db: AsyncSession = Depends(get_db)):
    event = payload.Event
    upload = event.get("Upload", {})
    metadata = _decode_tus_metadata(upload.get("MetaData", ""))

    file_path = upload.get("Storage", {}).get("Path") or metadata.get("path") or ""
    file_size = int(upload.get("Size") or 0)
    filename = metadata.get("filename") or Path(file_path).name

    probed = {}
    if file_path and Path(file_path).exists():
        probed = probe_video(file_path)

    clip = Clip(
        filename=filename,
        original_path=file_path,
        file_size=file_size,
        source=ClipSource.web_upload,
        ingest_status=ClipIngestStatus.staged,
        duration=probed.get("duration"),
        codec=probed.get("codec"),
        resolution=probed.get("resolution"),
        fps=probed.get("fps"),
        bitrate=probed.get("bitrate"),
    )
    db.add(clip)
    await db.flush()

    db.add_all(
        [
            IngestJob(clip_id=clip.id, job_type=JobType.transcribe),
            IngestJob(clip_id=clip.id, job_type=JobType.proxy),
        ]
    )

    await db.commit()
    await db.refresh(clip)

    transcribe_clip.delay(clip.id)
    generate_proxy.delay(clip.id)

    return {"ok": True, "clip_id": clip.id}

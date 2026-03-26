from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery(
    "indygestion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.task_routes = {
    "tasks.transcribe.transcribe_clip": {"queue": "transcribe"},
    "tasks.proxy.generate_proxy": {"queue": "proxy"},
    "tasks.embed.embed_clip": {"queue": "embed"},
    "tasks.archive.archive_project": {"queue": "archive"},
}


@celery_app.task(name="tasks.transcribe.transcribe_clip")
def transcribe_clip(clip_id: int) -> dict:
    return {"clip_id": clip_id, "status": "queued"}


@celery_app.task(name="tasks.proxy.generate_proxy")
def generate_proxy(clip_id: int) -> dict:
    return {"clip_id": clip_id, "status": "queued"}


@celery_app.task(name="tasks.embed.embed_clip")
def embed_clip(clip_id: int) -> dict:
    return {"clip_id": clip_id, "status": "queued"}


@celery_app.task(name="tasks.archive.archive_project")
def archive_project(project_id: int, preset: dict) -> dict:
    return {"project_id": project_id, "preset": preset, "status": "queued"}

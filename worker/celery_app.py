import os
import sys

# Ensure /app is on the Python path so 'tasks' and 'utils' are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "indygestion-worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "tasks.proxy",
        "tasks.transcribe",
        "tasks.embed",
        "tasks.cluster",
        "tasks.archive",
        "tasks.pipeline",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=60 * 60 * 8,
    task_soft_time_limit=60 * 60 * 7,
)

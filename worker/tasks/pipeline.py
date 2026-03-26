from __future__ import annotations

from celery import chain, group, shared_task

from tasks.archive import archive_project
from tasks.cluster import cluster_clip
from tasks.embed import embed_clip
from tasks.proxy import generate_proxy
from tasks.transcribe import transcribe_clip


@shared_task(name="tasks.pipeline.ingest_pipeline")
def ingest_pipeline(clip_id: int) -> dict:
    transcribe_chain = chain(
        transcribe_clip.si(clip_id, False),
        embed_clip.si(clip_id, False),
        cluster_clip.si(clip_id),
    )

    # Run proxy in parallel with the transcript/embed/cluster chain.
    workflow = group(
        transcribe_chain,
        generate_proxy.si(clip_id),
    )

    result = workflow.apply_async()
    return {"clip_id": clip_id, "workflow_id": result.id}


@shared_task(name="tasks.pipeline.archive_pipeline")
def archive_pipeline(project_id: int, preset: dict) -> dict:
    result = archive_project.delay(project_id, preset)
    return {"project_id": project_id, "task_id": result.id}

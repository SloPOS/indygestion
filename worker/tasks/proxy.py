from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from celery import shared_task
from sqlalchemy import text

from tasks import db_session, update_ingest_job
from utils.ffmpeg import build_proxy_command, check_qsv_available, probe_file

LOGGER = logging.getLogger(__name__)
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/media/indygestion"))


@shared_task(bind=True, name="tasks.proxy.generate_proxy", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def generate_proxy(self, clip_id: int) -> dict:
    worker_id = self.request.hostname
    self.update_state(state="PROGRESS", meta={"progress": 5, "stage": "loading_clip"})

    with db_session() as session:
        clip = session.execute(
            text("SELECT id, filename, original_path, project_id FROM clips WHERE id=:clip_id"), {"clip_id": clip_id}
        ).mappings().first()
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")

        original_path = Path(clip["original_path"])
        if not original_path.exists():
            raise FileNotFoundError(f"Original file missing: {original_path}")

        project = session.execute(
            text("SELECT id, folder_path FROM projects WHERE id=:project_id"), {"project_id": clip["project_id"]}
        ).mappings().first()

        project_root = Path(project["folder_path"]) if project and project.get("folder_path") else MEDIA_ROOT / "_review"
        proxies_dir = project_root / "proxies"
        proxies_dir.mkdir(parents=True, exist_ok=True)

        stem = original_path.stem
        output_path = proxies_dir / f"{stem}_proxy.mp4"

        session.execute(
            text("UPDATE clips SET proxy_status='processing', updated_at=NOW() WHERE id=:clip_id"), {"clip_id": clip_id}
        )
        update_ingest_job(
            session,
            clip_id=clip_id,
            project_id=clip["project_id"],
            job_type="proxy",
            status="running",
            progress=10,
            worker_id=worker_id,
        )

    self.update_state(state="PROGRESS", meta={"progress": 20, "stage": "probing_source"})
    source_info = probe_file(str(original_path))

    use_qsv = check_qsv_available()
    cmd = build_proxy_command(str(original_path), str(output_path), use_qsv=use_qsv)

    self.update_state(state="PROGRESS", meta={"progress": 50, "stage": "encoding", "qsv": use_qsv})
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and use_qsv:
        LOGGER.warning("QSV proxy encode failed; retrying with libx264. clip_id=%s error=%s", clip_id, result.stderr)
        cmd = build_proxy_command(str(original_path), str(output_path), use_qsv=False)
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        with db_session() as session:
            session.execute(
                text("UPDATE clips SET proxy_status='failed', updated_at=NOW() WHERE id=:clip_id"), {"clip_id": clip_id}
            )
            update_ingest_job(
                session,
                clip_id=clip_id,
                project_id=None,
                job_type="proxy",
                status="failed",
                progress=100,
                worker_id=worker_id,
                error_message=result.stderr[:4000],
            )
        raise RuntimeError(f"Proxy generation failed for clip {clip_id}: {result.stderr.strip()}")

    proxy_info = probe_file(str(output_path))

    with db_session() as session:
        session.execute(
            text(
                """
                UPDATE clips
                SET proxy_path=:proxy_path,
                    proxy_status='ready',
                    updated_at=NOW()
                WHERE id=:clip_id
                """
            ),
            {"proxy_path": str(output_path), "clip_id": clip_id},
        )
        update_ingest_job(
            session,
            clip_id=clip_id,
            project_id=None,
            job_type="proxy",
            status="completed",
            progress=100,
            worker_id=worker_id,
        )

    self.update_state(state="PROGRESS", meta={"progress": 100, "stage": "completed"})
    return {
        "clip_id": clip_id,
        "proxy_path": str(output_path),
        "used_qsv": use_qsv,
        "source": source_info,
        "proxy": proxy_info,
    }

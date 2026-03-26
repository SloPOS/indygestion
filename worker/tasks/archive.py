from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

from celery import shared_task
from sqlalchemy import text

from tasks import db_session, update_ingest_job
from utils.checksum import sha256_file
from utils.ffmpeg import build_archive_command, check_qsv_available, probe_file

LOGGER = logging.getLogger(__name__)
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/media/indygestion"))


@shared_task(bind=True, name="tasks.archive.archive_project")
def archive_project(self, project_id: int, preset: dict) -> dict:
    codec = (preset or {}).get("codec", "h265")
    crf = int((preset or {}).get("crf", 18))
    worker_id = self.request.hostname

    with db_session() as session:
        project = session.execute(
            text("SELECT id, name, folder_path FROM projects WHERE id=:project_id"), {"project_id": project_id}
        ).mappings().first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        session.execute(
            text("UPDATE projects SET status='archiving', archive_preset=:preset::jsonb, updated_at=NOW() WHERE id=:project_id"),
            {"preset": json.dumps(preset or {}), "project_id": project_id},
        )
        update_ingest_job(
            session,
            clip_id=None,
            project_id=project_id,
            job_type="archive",
            status="running",
            progress=5,
            worker_id=worker_id,
        )

        clips = session.execute(
            text("SELECT id, original_path, filename FROM clips WHERE project_id=:project_id ORDER BY id"),
            {"project_id": project_id},
        ).mappings().all()

    if not clips:
        raise ValueError(f"Project {project_id} has no clips")

    archive_root = MEDIA_ROOT / "archive" / f"project_{project_id}"
    archive_root.mkdir(parents=True, exist_ok=True)

    use_qsv = check_qsv_available()
    completed = []

    for idx, clip in enumerate(clips, start=1):
        progress_base = 10 + int((idx - 1) / len(clips) * 80)
        self.update_state(state="PROGRESS", meta={"progress": progress_base, "clip_id": clip["id"], "stage": "encoding"})

        src = Path(clip["original_path"])
        if not src.exists():
            raise FileNotFoundError(f"Missing source clip: {src}")

        ext = ".mov" if codec.lower() in {"dnxhd", "dnxhr"} else ".mp4"
        temp_out = archive_root / f"{src.stem}.tmp{ext}"
        final_out = archive_root / f"{src.stem}{ext}"

        cmd = build_archive_command(str(src), str(temp_out), codec=codec, crf=crf, use_qsv=use_qsv)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 and codec.lower() in {"h265", "hevc", "h265_qsv", "hevc_qsv"} and use_qsv:
            LOGGER.warning("QSV archive encode failed, retrying with libx265 for clip=%s", clip["id"])
            cmd = build_archive_command(str(src), str(temp_out), codec=codec, crf=crf, use_qsv=False)
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Archive encode failed for clip {clip['id']}: {result.stderr.strip()}")

        self.update_state(state="PROGRESS", meta={"progress": progress_base + 8, "clip_id": clip["id"], "stage": "verifying"})
        src_info = probe_file(str(src))
        out_info = probe_file(str(temp_out))

        frame_diff = abs((src_info.get("frame_count") or 0) - (out_info.get("frame_count") or 0))
        duration_diff = abs((src_info.get("duration") or 0) - (out_info.get("duration") or 0))
        if frame_diff > 3 or duration_diff > 0.25:
            raise RuntimeError(
                f"Verification failed for clip {clip['id']}: frame_diff={frame_diff}, duration_diff={duration_diff:.3f}s"
            )

        shutil.move(str(temp_out), str(final_out))

        with db_session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO file_operations (clip_id, operation, source_path, dest_path, performed_at, reversible_until, undone)
                    VALUES (:clip_id, 'archive', :source_path, :dest_path, NOW(), NOW() + interval '24 hours', false)
                    """
                ),
                {"clip_id": clip["id"], "source_path": str(src), "dest_path": str(final_out)},
            )

        completed.append(
            {
                "clip_id": clip["id"],
                "source": str(src),
                "archive_path": str(final_out),
                "source_sha256": sha256_file(src),
                "archive_sha256": sha256_file(final_out),
            }
        )

    with db_session() as session:
        session.execute(
            text(
                """
                UPDATE projects
                SET status='archived', archive_path=:archive_path, archived_at=NOW(), updated_at=NOW()
                WHERE id=:project_id
                """
            ),
            {"archive_path": str(archive_root), "project_id": project_id},
        )
        session.execute(
            text("UPDATE clips SET ingest_status='archived', updated_at=NOW() WHERE project_id=:project_id"),
            {"project_id": project_id},
        )
        update_ingest_job(
            session,
            clip_id=None,
            project_id=project_id,
            job_type="archive",
            status="completed",
            progress=100,
            worker_id=worker_id,
        )

    self.update_state(state="PROGRESS", meta={"progress": 100, "stage": "completed"})
    return {
        "project_id": project_id,
        "codec": codec,
        "crf": crf,
        "archived_clips": len(completed),
        "archive_root": str(archive_root),
        "files": completed,
    }

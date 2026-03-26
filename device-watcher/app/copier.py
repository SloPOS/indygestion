from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

import requests

logger = logging.getLogger(__name__)


class CopyError(RuntimeError):
    pass


class RsyncCopier:
    PROGRESS_RE = re.compile(r"(?P<bytes>[\d,]+)\s+(?P<pct>\d+)%")

    def __init__(self, staging_path: str, backend_url: str, request_timeout: int = 10) -> None:
        self.staging_path = Path(staging_path)
        self.staging_path.mkdir(parents=True, exist_ok=True)
        self.backend_url = backend_url.rstrip("/")
        self.request_timeout = request_timeout

    def copy(
        self,
        *,
        device_id: str,
        source_root: str,
        files: list[dict],
        on_progress: Callable[[dict], None] | None = None,
        stop_event: threading.Event | None = None,
    ) -> dict:
        session_id = f"ingest-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        destination = self.staging_path / session_id
        destination.mkdir(parents=True, exist_ok=True)

        if stop_event and stop_event.is_set():
            raise CopyError("Copy cancelled before start")

        total_bytes = sum(int(f.get("size", 0)) for f in files)
        copied_bytes_estimate = 0

        rsync_cmd = [
            "rsync",
            "-a",
            "--partial",
            "--append-verify",
            "--info=progress2,name0",
            "--checksum",
            f"{source_root.rstrip('/')}/",
            f"{str(destination)}/",
        ]

        logger.info("Starting rsync for device=%s into %s", device_id, destination)
        proc = subprocess.Popen(
            rsync_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        try:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                line = raw_line.strip()
                if not line:
                    continue

                if stop_event and stop_event.is_set():
                    proc.terminate()
                    raise CopyError("Copy cancelled by request")

                progress = self._parse_progress_line(line)
                if progress:
                    copied_bytes_estimate = max(copied_bytes_estimate, progress.get("bytes_done", 0))
                    payload = {
                        "device_id": device_id,
                        "session_id": session_id,
                        "stage": "copying",
                        "current_file_percent": progress.get("file_percent"),
                        "bytes_done": copied_bytes_estimate,
                        "total_bytes": total_bytes,
                        "total_percent": round((copied_bytes_estimate / total_bytes) * 100, 2) if total_bytes else 0.0,
                        "raw": line,
                    }
                    if on_progress:
                        on_progress(payload)

            code = proc.wait()
            if code != 0:
                raise CopyError(f"rsync failed with code {code}")

            verification = self._verify_files(source_root=source_root, destination_root=str(destination), files=files, on_progress=on_progress, device_id=device_id, session_id=session_id)
            result = {
                "device_id": device_id,
                "session_id": session_id,
                "destination": str(destination),
                "copied_files": len(files),
                "total_bytes": total_bytes,
                "verification": verification,
            }
            self._notify_backend("/api/v1/ingest/device/complete", result)
            return result
        finally:
            if proc.poll() is None:
                proc.kill()

    def _verify_files(
        self,
        *,
        source_root: str,
        destination_root: str,
        files: list[dict],
        on_progress: Callable[[dict], None] | None,
        device_id: str,
        session_id: str,
    ) -> dict:
        verified = 0
        mismatches: list[str] = []
        total = len(files)

        for index, item in enumerate(files, start=1):
            rel = item["path"]
            src = Path(source_root) / rel
            dst = Path(destination_root) / rel

            if not dst.exists():
                mismatches.append(rel)
                continue

            src_hash = self._sha256(src)
            dst_hash = self._sha256(dst)
            if src_hash != dst_hash:
                mismatches.append(rel)
            else:
                verified += 1

            if on_progress:
                on_progress(
                    {
                        "device_id": device_id,
                        "session_id": session_id,
                        "stage": "verifying",
                        "verified": verified,
                        "total": total,
                        "percent": round((index / total) * 100, 2) if total else 100.0,
                        "file": rel,
                    }
                )

        if mismatches:
            raise CopyError(f"SHA-256 verification failed for {len(mismatches)} files")

        return {"verified": verified, "total": total, "mismatches": mismatches}

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _notify_backend(self, endpoint: str, payload: dict) -> None:
        if not self.backend_url:
            return
        url = f"{self.backend_url}{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=self.request_timeout)
            if response.status_code >= 400:
                logger.warning("Backend notify failed (%s): %s", response.status_code, response.text)
        except requests.RequestException:
            logger.exception("Failed notifying backend at %s", url)

    def _parse_progress_line(self, line: str) -> dict | None:
        # Example:  1,234,567  23%   12.34MB/s    0:00:10
        m = self.PROGRESS_RE.search(line)
        if not m:
            return None
        try:
            bytes_done = int(m.group("bytes").replace(",", ""))
            pct = int(m.group("pct"))
            return {"bytes_done": bytes_done, "file_percent": pct}
        except ValueError:
            return None

    def cleanup_session(self, destination: str) -> None:
        path = Path(destination)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SKIP_DIR_NAMES = {
    ".trash",
    ".trashes",
    ".spotlight-v100",
    ".fseventsd",
    "@eadir",
    "__macosx",
    "thumbnails",
    "proxy",
}

SKIP_FILE_PREFIXES = {".", "thumb", "thumbnail", "._"}

CAMERA_ROOT_HINTS = {"dcim", "private", "clip", "contents", "avchd", "xdroot"}


class DeviceScanner:
    def __init__(self, video_extensions: list[str], min_file_size_bytes: int) -> None:
        self.video_extensions = {ext.lower() for ext in video_extensions}
        self.min_file_size_bytes = max(0, int(min_file_size_bytes))

    def update_config(self, *, video_extensions: list[str] | None = None, min_file_size_bytes: int | None = None) -> None:
        if video_extensions is not None:
            self.video_extensions = {ext.lower() for ext in video_extensions}
        if min_file_size_bytes is not None:
            self.min_file_size_bytes = max(0, int(min_file_size_bytes))

    def scan(self, mountpoint: str) -> list[dict]:
        root = Path(mountpoint)
        if not root.exists() or not root.is_dir():
            return []

        files: list[dict] = []
        for path in root.rglob("*"):
            try:
                if not path.is_file():
                    continue
                if self._should_skip(path):
                    continue
                if path.suffix.lower() not in self.video_extensions:
                    continue

                st = path.stat()
                if st.st_size < self.min_file_size_bytes:
                    continue

                modified = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
                rel_path = str(path.relative_to(root))
                files.append(
                    {
                        "path": rel_path,
                        "filename": path.name,
                        "size": st.st_size,
                        "modified_date": modified,
                        "camera_structure_hint": self._camera_structure_hint(rel_path),
                    }
                )
            except FileNotFoundError:
                # Device can disappear while scanning.
                logger.warning("File vanished during scan: %s", path)
            except PermissionError:
                logger.warning("Permission denied while scanning file: %s", path)
            except Exception:
                logger.exception("Unexpected scan error on path: %s", path)

        files.sort(key=lambda f: f["path"])
        return files

    def _should_skip(self, path: Path) -> bool:
        parts = [p.lower() for p in path.parts]
        for part in parts:
            if part.startswith("."):
                return True
            if part in SKIP_DIR_NAMES:
                return True

        name = path.name.lower()
        for prefix in SKIP_FILE_PREFIXES:
            if name.startswith(prefix):
                return True
        if name in {"thumbs.db", ".ds_store"}:
            return True

        return False

    @staticmethod
    def _camera_structure_hint(rel_path: str) -> str | None:
        lowered = rel_path.lower()
        for hint in CAMERA_ROOT_HINTS:
            token = f"{hint}/"
            if lowered.startswith(token) or f"/{token}" in lowered:
                return hint.upper()
        return None

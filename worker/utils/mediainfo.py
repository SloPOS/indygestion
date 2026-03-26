from __future__ import annotations

from utils.ffmpeg import probe_file


def extract_media_info(path: str) -> dict:
    """Thin wrapper around ffprobe-based probing for future expansion."""
    return probe_file(path)

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Any

DEFAULT_EXTENSIONS = [".mov", ".mp4", ".mxf", ".avi", ".braw", ".mts", ".m4v"]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got: {raw!r}") from exc
    if value < minimum:
        raise ValueError(f"Environment variable {name} must be >= {minimum}, got: {value}")
    return value


def _parse_extensions(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_EXTENSIONS.copy()
    exts: list[str] = []
    for part in value.split(","):
        part = part.strip().lower()
        if not part:
            continue
        if not part.startswith("."):
            part = f".{part}"
        exts.append(part)
    unique = sorted(set(exts))
    return unique if unique else DEFAULT_EXTENSIONS.copy()


@dataclass(slots=True)
class Settings:
    backend_url: str = "http://backend:8000"
    staging_path: str = "/media/indygestion/staging"
    auto_ingest: bool = False
    video_extensions: list[str] = field(default_factory=lambda: DEFAULT_EXTENSIONS.copy())
    min_file_size_mb: int = 10
    mount_base: str = "/tmp/indygestion-mount"
    api_host: str = "0.0.0.0"
    api_port: int = 8100

    @property
    def min_file_size_bytes(self) -> int:
        return self.min_file_size_mb * 1024 * 1024

    def update(self, *, auto_ingest: bool | None = None, video_extensions: list[str] | None = None, min_file_size_mb: int | None = None) -> None:
        if auto_ingest is not None:
            self.auto_ingest = bool(auto_ingest)
        if video_extensions is not None:
            normalized = _parse_extensions(",".join(video_extensions))
            self.video_extensions = normalized
        if min_file_size_mb is not None:
            if min_file_size_mb < 0:
                raise ValueError("min_file_size_mb must be >= 0")
            self.min_file_size_mb = int(min_file_size_mb)

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["min_file_size_bytes"] = self.min_file_size_bytes
        return data


def load_settings() -> Settings:
    return Settings(
        backend_url=os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/"),
        staging_path=os.getenv("STAGING_PATH", "/media/indygestion/staging"),
        auto_ingest=_env_bool("AUTO_INGEST", False),
        video_extensions=_parse_extensions(os.getenv("VIDEO_EXTENSIONS")),
        min_file_size_mb=_env_int("MIN_FILE_SIZE_MB", 10, minimum=0),
        mount_base=os.getenv("MOUNT_BASE", "/tmp/indygestion-mount"),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=_env_int("API_PORT", 8100, minimum=1),
    )

import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProxyStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class ClipSource(str, enum.Enum):
    web_upload = "web_upload"
    usb_ingest = "usb_ingest"
    sd_ingest = "sd_ingest"


class ClipIngestStatus(str, enum.Enum):
    uploading = "uploading"
    staged = "staged"
    transcribing = "transcribing"
    reviewing = "reviewing"
    assigned = "assigned"
    archived = "archived"


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    ingest_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingest_sessions.id", ondelete="SET NULL"), index=True
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(default=0)
    duration: Mapped[float | None] = mapped_column()
    resolution: Mapped[str | None] = mapped_column(String(64))
    codec: Mapped[str | None] = mapped_column(String(64))
    fps: Mapped[float | None] = mapped_column()
    bitrate: Mapped[int | None] = mapped_column(Integer)

    proxy_path: Mapped[str | None] = mapped_column(String(1024))
    proxy_status: Mapped[ProxyStatus] = mapped_column(
        Enum(ProxyStatus, name="proxy_status_enum"), default=ProxyStatus.pending
    )

    transcript_text: Mapped[str | None] = mapped_column(Text)
    transcript_json_path: Mapped[str | None] = mapped_column(String(1024))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))

    checksum_sha256: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[ClipSource] = mapped_column(Enum(ClipSource, name="clip_source_enum"), default=ClipSource.web_upload)
    source_device: Mapped[str | None] = mapped_column(String(255))
    ingest_status: Mapped[ClipIngestStatus] = mapped_column(
        Enum(ClipIngestStatus, name="clip_ingest_status_enum"), default=ClipIngestStatus.uploading, index=True
    )
    similarity_matches: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project", back_populates="clips")
    ingest_session = relationship("IngestSession", back_populates="clips")
    jobs = relationship("IngestJob", back_populates="clip", cascade="all, delete-orphan")

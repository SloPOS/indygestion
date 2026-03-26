import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngestSource(str, enum.Enum):
    web = "web"
    usb = "usb"
    sd = "sd"


class IngestSessionStatus(str, enum.Enum):
    active = "active"
    complete = "complete"


class IngestSession(Base):
    __tablename__ = "ingest_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source: Mapped[IngestSource] = mapped_column(Enum(IngestSource, name="ingest_source_enum"), index=True)
    device_info: Mapped[dict | None] = mapped_column(JSONB)
    clip_count: Mapped[int] = mapped_column(Integer, default=0)
    total_size: Mapped[int] = mapped_column(default=0)
    status: Mapped[IngestSessionStatus] = mapped_column(
        Enum(IngestSessionStatus, name="ingest_session_status_enum"), default=IngestSessionStatus.active
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clips = relationship("Clip", back_populates="ingest_session")

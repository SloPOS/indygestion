import enum
from datetime import datetime, timedelta

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FileOperationType(str, enum.Enum):
    move = "move"
    copy = "copy"
    delete = "delete"
    archive = "archive"


class FileOperation(Base):
    __tablename__ = "file_operations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    clip_id: Mapped[int | None] = mapped_column(ForeignKey("clips.id", ondelete="SET NULL"), index=True)
    operation: Mapped[FileOperationType] = mapped_column(Enum(FileOperationType, name="file_operation_enum"))
    source_path: Mapped[str] = mapped_column(String(1024))
    dest_path: Mapped[str | None] = mapped_column(String(1024))
    undone: Mapped[bool] = mapped_column(Boolean, default=False)

    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reversible_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow() + timedelta(hours=24)
    )

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_operation import FileOperation, FileOperationType


async def _log_operation(
    db: AsyncSession,
    clip_id: int | None,
    operation: FileOperationType,
    source_path: str,
    dest_path: str | None,
    reversible_hours: int = 24,
) -> FileOperation:
    op = FileOperation(
        clip_id=clip_id,
        operation=operation,
        source_path=source_path,
        dest_path=dest_path,
        reversible_until=datetime.utcnow() + timedelta(hours=reversible_hours),
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return op


async def move_file(db: AsyncSession, source: str, dest: str, clip_id: int | None = None) -> FileOperation:
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(source, dest)
    return await _log_operation(db, clip_id, FileOperationType.move, source, dest)


async def copy_file(db: AsyncSession, source: str, dest: str, clip_id: int | None = None) -> FileOperation:
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return await _log_operation(db, clip_id, FileOperationType.copy, source, dest)


async def delete_file(db: AsyncSession, source: str, clip_id: int | None = None) -> FileOperation:
    Path(source).unlink(missing_ok=True)
    return await _log_operation(db, clip_id, FileOperationType.delete, source, None)


async def undo_operation(db: AsyncSession, op: FileOperation) -> bool:
    if op.undone or op.reversible_until < datetime.utcnow():
        return False

    if op.operation == FileOperationType.move and op.dest_path:
        if Path(op.dest_path).exists():
            Path(op.source_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(op.dest_path, op.source_path)
    elif op.operation == FileOperationType.copy and op.dest_path:
        Path(op.dest_path).unlink(missing_ok=True)
    elif op.operation == FileOperationType.delete:
        return False

    op.undone = True
    await db.commit()
    return True

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.file_operation import FileOperation
from app.services.storage import undo_operation

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/file-operations")
async def list_file_operations(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(FileOperation.id)))
    rows = (
        await db.scalars(
            select(FileOperation).order_by(FileOperation.performed_at.desc()).offset(offset).limit(limit)
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "clip_id": r.clip_id,
                "operation": r.operation,
                "source_path": r.source_path,
                "dest_path": r.dest_path,
                "performed_at": r.performed_at,
                "reversible_until": r.reversible_until,
                "undone": r.undone,
            }
            for r in rows
        ],
        "total": total or 0,
        "offset": offset,
        "limit": limit,
    }


@router.post("/file-operations/{operation_id}/undo")
async def undo_file_operation(operation_id: int, db: AsyncSession = Depends(get_db)):
    op = await db.get(FileOperation, operation_id)
    if not op:
        raise HTTPException(status_code=404, detail="File operation not found")

    success = await undo_operation(db, op)
    if not success:
        raise HTTPException(status_code=400, detail="Operation cannot be undone")
    return {"ok": True, "operation_id": op.id}

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ingest_session import IngestSession, IngestSource
from app.models.setting import AppSetting

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/status")
async def device_status(db: AsyncSession = Depends(get_db)):
    recent = (
        await db.scalars(
            select(IngestSession)
            .where(IngestSession.source.in_([IngestSource.usb, IngestSource.sd]))
            .order_by(IngestSession.started_at.desc())
            .limit(10)
        )
    ).all()

    auto_ingest = await db.get(AppSetting, "auto_ingest_enabled")
    auto_ingest_enabled = auto_ingest.value_bool if auto_ingest else False

    return {
        "auto_ingest_enabled": auto_ingest_enabled,
        "recent_device_sessions": [
            {
                "id": s.id,
                "source": s.source,
                "device_info": s.device_info,
                "status": s.status,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
            }
            for s in recent
        ],
    }


@router.post("/auto-ingest")
async def configure_auto_ingest(enabled: bool, db: AsyncSession = Depends(get_db)):
    setting = await db.get(AppSetting, "auto_ingest_enabled")
    if not setting:
        setting = AppSetting(key="auto_ingest_enabled", value_type="bool", value_bool=enabled)
        db.add(setting)
    else:
        setting.value_bool = enabled
    await db.commit()
    return {"auto_ingest_enabled": enabled}

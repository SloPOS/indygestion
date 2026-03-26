from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.setting import AppSetting
from app.schemas.settings import AppSettingsResponse, DEFAULT_SETTINGS, SettingResponse, SettingUpsert

router = APIRouter(prefix="/settings", tags=["settings"])


def _value_from_setting(setting: AppSetting) -> Any:
    if setting.value_type == "int":
        return setting.value_int
    if setting.value_type == "float":
        return setting.value_float
    if setting.value_type == "bool":
        return setting.value_bool
    return setting.value_text


def _apply_value(setting: AppSetting, value: Any, value_type: str):
    setting.value_type = value_type
    setting.value_text = None
    setting.value_int = None
    setting.value_float = None
    setting.value_bool = None

    if value_type == "int":
        setting.value_int = int(value)
    elif value_type == "float":
        setting.value_float = float(value)
    elif value_type == "bool":
        setting.value_bool = bool(value)
    else:
        setting.value_text = str(value)


@router.post("/init-defaults", response_model=AppSettingsResponse)
async def init_defaults(db: AsyncSession = Depends(get_db)):
    for key, (value_type, value) in DEFAULT_SETTINGS.items():
        row = await db.get(AppSetting, key)
        if row:
            continue
        row = AppSetting(key=key, value_type=value_type)
        _apply_value(row, value, value_type)
        db.add(row)
    await db.commit()
    return await list_settings(db)


@router.get("", response_model=AppSettingsResponse)
async def list_settings(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(AppSetting).order_by(AppSetting.key.asc()))).all()
    response = [
        SettingResponse(key=r.key, value_type=r.value_type, value=_value_from_setting(r), updated_at=r.updated_at) for r in rows
    ]
    return AppSettingsResponse(settings=response)


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(AppSetting, key)
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    return SettingResponse(key=row.key, value_type=row.value_type, value=_value_from_setting(row), updated_at=row.updated_at)


@router.put("/{key}", response_model=SettingResponse)
async def upsert_setting(key: str, payload: SettingUpsert, db: AsyncSession = Depends(get_db)):
    row = await db.get(AppSetting, key)
    if not row:
        row = AppSetting(key=key, value_type="str")
        db.add(row)

    value_type = payload.value_type
    if not value_type:
        default = DEFAULT_SETTINGS.get(key)
        value_type = default[0] if default else "str"

    _apply_value(row, payload.value, value_type)
    await db.commit()
    await db.refresh(row)
    return SettingResponse(key=row.key, value_type=row.value_type, value=_value_from_setting(row), updated_at=row.updated_at)

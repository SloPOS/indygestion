from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CoordinatorProtocol(Protocol):
    def list_devices(self) -> list[dict[str, Any]]: ...

    def get_device_files(self, device_id: str) -> list[dict[str, Any]]: ...

    def start_ingest(self, device_id: str) -> dict[str, Any]: ...

    def eject_device(self, device_id: str) -> dict[str, Any]: ...

    def get_status(self) -> dict[str, Any]: ...

    def update_runtime_config(self, *, auto_ingest: bool | None, video_extensions: list[str] | None, min_file_size_mb: int | None) -> dict[str, Any]: ...


class ConfigUpdateRequest(BaseModel):
    auto_ingest: bool | None = None
    video_extensions: list[str] | None = None
    min_file_size_mb: int | None = Field(default=None, ge=0)


class EventBus:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        message = json.dumps(event, default=str)
        async with self._lock:
            clients = list(self._clients)
        stale: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_text(message)
            except Exception:
                stale.append(client)
        if stale:
            async with self._lock:
                for client in stale:
                    self._clients.discard(client)



def create_app(coordinator: CoordinatorProtocol, event_bus: EventBus) -> FastAPI:
    app = FastAPI(title="Indygestion Device Watcher", version="0.1.0")

    @app.get("/devices")
    async def list_devices() -> list[dict[str, Any]]:
        return coordinator.list_devices()

    @app.get("/devices/{device_id}/files")
    async def list_device_files(device_id: str) -> list[dict[str, Any]]:
        try:
            return coordinator.get_device_files(device_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Device not found")

    @app.post("/devices/{device_id}/ingest")
    async def ingest_device(device_id: str) -> dict[str, Any]:
        try:
            return coordinator.start_ingest(device_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Device not found")
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @app.post("/devices/{device_id}/eject")
    async def eject_device(device_id: str) -> dict[str, Any]:
        try:
            return coordinator.eject_device(device_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Device not found")
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return coordinator.get_status()

    @app.put("/config")
    async def update_config(payload: ConfigUpdateRequest) -> dict[str, Any]:
        return coordinator.update_runtime_config(
            auto_ingest=payload.auto_ingest,
            video_extensions=payload.video_extensions,
            min_file_size_mb=payload.min_file_size_mb,
        )

    @app.websocket("/ws/events")
    async def events_ws(websocket: WebSocket) -> None:
        await event_bus.register(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected")
        finally:
            await event_bus.unregister(websocket)

    return app

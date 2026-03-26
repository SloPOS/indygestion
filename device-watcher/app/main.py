from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests
import uvicorn

from .api import EventBus, create_app
from .config import Settings, load_settings
from .copier import CopyError, RsyncCopier
from .mounter import DeviceMounter, MountError
from .scanner import DeviceScanner
from .watcher import DeviceInfo, DeviceWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ManagedDevice:
    info: DeviceInfo
    status: str = "detected"
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mountpoint: str | None = None
    files: list[dict] = field(default_factory=list)
    last_error: str | None = None
    ingest_session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.info.device_id,
            "devname": self.info.devname,
            "label": self.info.label,
            "serial": self.info.serial,
            "fs_type": self.info.fs_type,
            "size_bytes": self.info.size_bytes,
            "model": self.info.model,
            "vendor": self.info.vendor,
            "bus": self.info.bus,
            "status": self.status,
            "connected_at": self.connected_at,
            "mountpoint": self.mountpoint,
            "file_count": len(self.files),
            "last_error": self.last_error,
            "ingest_session_id": self.ingest_session_id,
        }


class DeviceCoordinator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._event_bus = EventBus()
        self._mounter = DeviceMounter(settings.mount_base)
        self._scanner = DeviceScanner(settings.video_extensions, settings.min_file_size_bytes)
        self._copier = RsyncCopier(settings.staging_path, settings.backend_url)
        self._watcher = DeviceWatcher(on_add=self._on_device_add, on_remove=self._on_device_remove)

        self._devices: dict[str, ManagedDevice] = {}
        self._ingest_cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ingest")
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def start(self) -> None:
        self._watcher.start()

    def stop(self) -> None:
        self._watcher.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def list_devices(self) -> list[dict[str, Any]]:
        with self._lock:
            return [d.to_dict() for d in self._devices.values()]

    def get_device_files(self, device_id: str) -> list[dict[str, Any]]:
        with self._lock:
            if device_id not in self._devices:
                raise KeyError(device_id)
            return list(self._devices[device_id].files)

    def start_ingest(self, device_id: str) -> dict[str, Any]:
        with self._lock:
            device = self._require_device(device_id)
            if device.status in {"ingesting", "ejecting"}:
                raise RuntimeError(f"Device {device_id} is currently {device.status}")
            if not device.mountpoint:
                raise RuntimeError("Device is not mounted")
            if not device.files:
                raise RuntimeError("No eligible files found on device")

            device.status = "ingesting"
            device.last_error = None
            cancel_event = threading.Event()
            self._ingest_cancel_events[device_id] = cancel_event

        self._emit_event({"type": "ingest_started", "device_id": device_id})
        self._notify_backend("/api/v1/device/ingest-started", {"device_id": device_id, "files": len(device.files)})

        self._executor.submit(self._run_ingest, device_id, cancel_event)
        return {"status": "started", "device_id": device_id}

    def eject_device(self, device_id: str) -> dict[str, Any]:
        with self._lock:
            device = self._require_device(device_id)
            if device.status == "ingesting":
                ev = self._ingest_cancel_events.get(device_id)
                if ev:
                    ev.set()
            device.status = "ejecting"

        self._safe_unmount(device_id)
        with self._lock:
            device = self._require_device(device_id)
            device.status = "ejected"

        self._emit_event({"type": "device_ejected", "device_id": device_id})
        return {"status": "ejected", "device_id": device_id}

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            ingesting = [d.info.device_id for d in self._devices.values() if d.status == "ingesting"]
            return {
                "health": "ok",
                "watcher_running": True,
                "connected_devices": len(self._devices),
                "active_ingests": ingesting,
                "config": self.settings.to_public_dict(),
            }

    def update_runtime_config(self, *, auto_ingest: bool | None, video_extensions: list[str] | None, min_file_size_mb: int | None) -> dict[str, Any]:
        self.settings.update(auto_ingest=auto_ingest, video_extensions=video_extensions, min_file_size_mb=min_file_size_mb)
        self._scanner.update_config(video_extensions=self.settings.video_extensions, min_file_size_bytes=self.settings.min_file_size_bytes)
        return self.settings.to_public_dict()

    def _on_device_add(self, info: DeviceInfo) -> None:
        with self._lock:
            existing = self._devices.get(info.device_id)
            if existing and existing.status not in {"disconnected", "ejected"}:
                logger.debug("Ignoring duplicate add for %s", info.device_id)
                return

            managed = ManagedDevice(info=info, status="detected")
            self._devices[info.device_id] = managed

        try:
            mountpoint = self._mounter.mount_read_only(info)
            files = self._scanner.scan(mountpoint)
            with self._lock:
                managed = self._devices[info.device_id]
                managed.mountpoint = mountpoint
                managed.files = files
                managed.status = "ready"

            payload = {
                "type": "device_connected",
                "device": managed.to_dict(),
                "files": files,
            }
            self._emit_event(payload)
            self._notify_backend(
                "/api/v1/device/connected",
                {
                    "device": managed.to_dict(),
                    "files": files,
                },
            )

            if self.settings.auto_ingest and files:
                self.start_ingest(info.device_id)
        except MountError as exc:
            with self._lock:
                managed = self._devices[info.device_id]
                managed.status = "error"
                managed.last_error = str(exc)
            self._emit_event({"type": "device_error", "device_id": info.device_id, "error": str(exc)})
        except Exception as exc:
            logger.exception("Failed processing add for %s", info.device_id)
            with self._lock:
                managed = self._devices[info.device_id]
                managed.status = "error"
                managed.last_error = str(exc)
            self._emit_event({"type": "device_error", "device_id": info.device_id, "error": str(exc)})

    def _on_device_remove(self, device_id: str) -> None:
        with self._lock:
            if device_id not in self._devices:
                return
            device = self._devices[device_id]
            device.status = "disconnected"

        ev = self._ingest_cancel_events.get(device_id)
        if ev:
            ev.set()
        self._safe_unmount(device_id)
        self._emit_event({"type": "device_disconnected", "device_id": device_id})
        self._notify_backend("/api/v1/device/disconnected", {"device_id": device_id})

    def _run_ingest(self, device_id: str, cancel_event: threading.Event) -> None:
        try:
            with self._lock:
                device = self._require_device(device_id)
                mountpoint = device.mountpoint
                files = list(device.files)
            if not mountpoint:
                raise RuntimeError("Device is not mounted")

            def on_progress(event: dict[str, Any]) -> None:
                self._emit_event({"type": "ingest_progress", **event})
                self._notify_backend("/api/v1/device/ingest-progress", event)

            result = self._copier.copy(
                device_id=device_id,
                source_root=mountpoint,
                files=files,
                on_progress=on_progress,
                stop_event=cancel_event,
            )

            with self._lock:
                device = self._require_device(device_id)
                device.status = "complete"
                device.ingest_session_id = result["session_id"]

            self._emit_event({"type": "ingest_complete", "device_id": device_id, "result": result})
            self._notify_backend("/api/v1/device/ingest-complete", result)
        except CopyError as exc:
            logger.warning("Ingest copy error for %s: %s", device_id, exc)
            with self._lock:
                if device_id in self._devices:
                    self._devices[device_id].status = "error"
                    self._devices[device_id].last_error = str(exc)
            self._emit_event({"type": "ingest_failed", "device_id": device_id, "error": str(exc)})
            self._notify_backend("/api/v1/device/ingest-failed", {"device_id": device_id, "error": str(exc)})
        except Exception as exc:
            logger.exception("Ingest crashed for %s", device_id)
            with self._lock:
                if device_id in self._devices:
                    self._devices[device_id].status = "error"
                    self._devices[device_id].last_error = str(exc)
            self._emit_event({"type": "ingest_failed", "device_id": device_id, "error": str(exc)})
            self._notify_backend("/api/v1/device/ingest-failed", {"device_id": device_id, "error": str(exc)})
        finally:
            with self._lock:
                self._ingest_cancel_events.pop(device_id, None)

    def _safe_unmount(self, device_id: str) -> None:
        with self._lock:
            device = self._devices.get(device_id)
            if not device or not device.mountpoint:
                return
            mountpoint = device.mountpoint
            info = device.info

        try:
            self._mounter.safe_eject(info, mountpoint)
        except Exception as exc:
            logger.warning("Failed safe eject for %s: %s", device_id, exc)
            with self._lock:
                if device_id in self._devices:
                    self._devices[device_id].last_error = str(exc)
        finally:
            with self._lock:
                if device_id in self._devices:
                    self._devices[device_id].mountpoint = None

    def _require_device(self, device_id: str) -> ManagedDevice:
        device = self._devices.get(device_id)
        if not device:
            raise KeyError(device_id)
        return device

    def _emit_event(self, event: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None:
            return

        async def _broadcast() -> None:
            await self._event_bus.broadcast(event)

        try:
            loop.call_soon_threadsafe(lambda: asyncio.create_task(_broadcast()))
        except RuntimeError:
            logger.debug("Event loop is closed; dropping event: %s", event.get("type"))

    def _notify_backend(self, endpoint: str, payload: dict[str, Any]) -> None:
        url = f"{self.settings.backend_url.rstrip('/')}{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code >= 400:
                logger.warning("Backend notification failed (%s): %s", response.status_code, response.text)
        except requests.RequestException:
            logger.exception("Could not notify backend: %s", url)


def run() -> None:
    settings = load_settings()
    coordinator = DeviceCoordinator(settings)
    app = create_app(coordinator, coordinator.event_bus)

    @app.on_event("startup")
    async def _startup() -> None:
        coordinator.set_event_loop(asyncio.get_running_loop())
        coordinator.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        coordinator.stop()

    uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_level="info")


if __name__ == "__main__":
    run()

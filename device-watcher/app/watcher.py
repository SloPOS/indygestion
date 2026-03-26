from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

import pyudev

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DeviceInfo:
    device_id: str
    devname: str
    syspath: str
    label: str
    serial: str
    fs_type: str
    size_bytes: int
    model: str
    vendor: str
    bus: str

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "devname": self.devname,
            "syspath": self.syspath,
            "label": self.label,
            "serial": self.serial,
            "fs_type": self.fs_type,
            "size_bytes": self.size_bytes,
            "model": self.model,
            "vendor": self.vendor,
            "bus": self.bus,
        }


class DeviceWatcher:
    def __init__(
        self,
        on_add: Callable[[DeviceInfo], None],
        on_remove: Callable[[str], None],
    ) -> None:
        self._on_add = on_add
        self._on_remove = on_remove
        self._context = pyudev.Context()
        self._monitor: pyudev.Monitor | None = None
        self._observer: pyudev.MonitorObserver | None = None
        self._lock = threading.Lock()
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            monitor = pyudev.Monitor.from_netlink(self._context)
            monitor.filter_by(subsystem="block")
            observer = pyudev.MonitorObserver(monitor, callback=self._on_udev_event, name="indygestion-udev")
            observer.start()
            self._monitor = monitor
            self._observer = observer
            self._started = True
        logger.info("Device watcher started")

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            if self._observer is not None:
                self._observer.stop()
            self._observer = None
            self._monitor = None
            self._started = False
        logger.info("Device watcher stopped")

    def _on_udev_event(self, action: str, device: pyudev.Device) -> None:
        try:
            if not self._is_candidate_partition(device):
                return

            if action in {"add", "change"}:
                info = self._build_device_info(device)
                if info:
                    logger.info("Detected removable partition add/change: %s", info.devname)
                    self._on_add(info)
            elif action == "remove":
                device_id = self._device_id(device)
                if device_id:
                    logger.info("Detected removable partition remove: %s", device_id)
                    self._on_remove(device_id)
        except Exception:
            logger.exception("Unhandled error processing udev event: action=%s, device=%s", action, device)

    def _is_candidate_partition(self, device: pyudev.Device) -> bool:
        if device.get("SUBSYSTEM") != "block":
            return False
        if device.get("DEVTYPE") != "partition":
            return False

        devname = (device.get("DEVNAME") or "").strip()
        if not devname:
            return False

        # Skip loop/ram/dm devices and obvious internal NVMe/SATA roots.
        if devname.startswith(("/dev/loop", "/dev/ram", "/dev/dm-")):
            return False

        if self._is_internal(device):
            return False

        return True

    def _is_internal(self, device: pyudev.Device) -> bool:
        removable = (device.get("ID_DRIVE_FLASH_SD") or device.get("ID_DRIVE_MEDIA_FLASH_SD") or "").strip()
        if removable == "1":
            return False

        parent_disk = device.find_parent("block")
        if parent_disk is None:
            return False

        removable_attr = None
        try:
            removable_attr = parent_disk.attributes.get("removable")
        except Exception:
            removable_attr = None
        if removable_attr is not None:
            try:
                if removable_attr.decode().strip() == "1":
                    return False
            except Exception:
                pass

        bus = (device.get("ID_BUS") or parent_disk.get("ID_BUS") or "").lower()
        if bus in {"usb", "mmc"}:
            return False

        devpath = (device.get("DEVPATH") or "").lower()
        if "/usb" in devpath or "/mmc" in devpath or "/sdhci" in devpath:
            return False

        return True

    def _build_device_info(self, device: pyudev.Device) -> DeviceInfo | None:
        devname = (device.get("DEVNAME") or "").strip()
        if not devname:
            return None

        label = (device.get("ID_FS_LABEL") or device.get("ID_FS_LABEL_ENC") or "").strip() or "UNLABELED"
        serial = (device.get("ID_SERIAL_SHORT") or device.get("ID_SERIAL") or "").strip()
        fs_type = (device.get("ID_FS_TYPE") or "").strip().lower()
        model = (device.get("ID_MODEL") or "").strip()
        vendor = (device.get("ID_VENDOR") or "").strip()
        bus = (device.get("ID_BUS") or "").strip().lower()

        size_bytes = 0
        try:
            sectors_raw = device.attributes.get("size")
            if sectors_raw:
                sectors = int(sectors_raw.decode().strip())
                size_bytes = sectors * 512
        except Exception:
            logger.debug("Unable to read size for %s", devname, exc_info=True)

        device_id = self._device_id(device)
        syspath = str(device.sys_path)

        return DeviceInfo(
            device_id=device_id,
            devname=devname,
            syspath=syspath,
            label=label,
            serial=serial,
            fs_type=fs_type,
            size_bytes=size_bytes,
            model=model,
            vendor=vendor,
            bus=bus,
        )

    @staticmethod
    def _device_id(device: pyudev.Device) -> str:
        return (
            (device.get("ID_FS_UUID") or "").strip()
            or (device.get("ID_PART_ENTRY_UUID") or "").strip()
            or (device.get("DEVNAME") or "").strip()
        )

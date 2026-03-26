from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from .watcher import DeviceInfo

logger = logging.getLogger(__name__)


class MountError(RuntimeError):
    pass


class DeviceMounter:
    def __init__(self, mount_base: str) -> None:
        self.mount_base = Path(mount_base)
        self.mount_base.mkdir(parents=True, exist_ok=True)

    def mount_read_only(self, device: DeviceInfo) -> str:
        if self._is_mounted_anywhere(device.devname):
            raise MountError(f"Device {device.devname} is already mounted elsewhere")

        mountpoint = self._mountpoint_for(device)
        mountpoint.mkdir(parents=True, exist_ok=True)

        fstype = self._normalized_fs(device.fs_type)
        mount_cmd = ["mount", "-o", "ro,nosuid,nodev,noexec"]
        if fstype:
            mount_cmd.extend(["-t", fstype])
        mount_cmd.extend([device.devname, str(mountpoint)])

        logger.info("Mounting %s at %s (fstype=%s)", device.devname, mountpoint, fstype or "auto")
        result = subprocess.run(mount_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise MountError(f"mount failed for {device.devname}: {stderr}")

        return str(mountpoint)

    def unmount(self, mountpoint: str) -> None:
        mp = Path(mountpoint)
        if not mp.exists():
            return

        subprocess.run(["sync"], capture_output=True, text=True)
        result = subprocess.run(["umount", str(mp)], capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if "not mounted" in stderr.lower():
                return
            raise MountError(f"umount failed for {mountpoint}: {stderr}")

        try:
            mp.rmdir()
        except OSError:
            logger.debug("Mountpoint not empty or not removable: %s", mountpoint)

    def safe_eject(self, device: DeviceInfo, mountpoint: str | None = None) -> None:
        if mountpoint:
            self.unmount(mountpoint)

        # Best effort power-off/eject; not all devices support this.
        eject = subprocess.run(["eject", device.devname], capture_output=True, text=True)
        if eject.returncode != 0:
            logger.info("eject returned non-zero for %s: %s", device.devname, (eject.stderr or "").strip())

    @staticmethod
    def _normalized_fs(fs_type: str | None) -> str | None:
        if not fs_type:
            return None
        fs = fs_type.lower().strip()
        mapping = {
            "vfat": "vfat",
            "fat": "vfat",
            "fat32": "vfat",
            "exfat": "exfat",
            "ntfs": "ntfs-3g",
            "hfsplus": "hfsplus",
            "hfs+": "hfsplus",
            "ext4": "ext4",
            "ext3": "ext3",
            "ext2": "ext2",
        }
        return mapping.get(fs, fs)

    def _mountpoint_for(self, device: DeviceInfo) -> Path:
        clean_label = re.sub(r"[^a-zA-Z0-9._-]+", "_", device.label).strip("_") or "device"
        suffix = re.sub(r"[^a-zA-Z0-9._-]+", "_", device.device_id).strip("_")[:24] or "unknown"
        return self.mount_base / f"{clean_label}-{suffix}"

    @staticmethod
    def _is_mounted_anywhere(devname: str) -> bool:
        with open("/proc/mounts", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.split(" ", 1)[0] == devname:
                    return True
        return False

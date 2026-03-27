"""Firmware binary storage and version management."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

FIRMWARE_DIR = "firmware"
FIRMWARE_FILENAME = "firmware.bin"
VERSION_FILENAME = "firmware.version"


class FirmwareManager:
    """Manage firmware binary storage and version tracking."""

    def __init__(self, base_dir: str) -> None:
        """Initialize with base directory for firmware storage."""
        self._firmware_dir = os.path.join(base_dir, FIRMWARE_DIR)

    def _ensure_dir(self) -> None:
        os.makedirs(self._firmware_dir, exist_ok=True)

    def _bin_path(self) -> str:
        return os.path.join(self._firmware_dir, FIRMWARE_FILENAME)

    def _version_path(self) -> str:
        return os.path.join(self._firmware_dir, VERSION_FILENAME)

    def get_firmware_info(self) -> dict[str, str | int] | None:
        """Get firmware version and size, or None if no firmware stored."""
        bin_path = self._bin_path()
        version_path = self._version_path()

        if not os.path.isfile(bin_path) or not os.path.isfile(version_path):
            return None

        version = Path(version_path).read_text().strip()
        size = os.path.getsize(bin_path)

        return {"version": version, "size": size}

    def get_firmware_path(self) -> str | None:
        """Get path to firmware binary, or None if not stored."""
        bin_path = self._bin_path()
        if os.path.isfile(bin_path):
            return bin_path
        return None

    def needs_update(self, device_version: str) -> bool:
        """Check if a device with the given version needs an update."""
        info = self.get_firmware_info()
        if info is None:
            return False
        return info["version"] != device_version

    def store_firmware(self, binary: bytes, version: str) -> None:
        """Store firmware binary and version."""
        self._ensure_dir()
        Path(self._bin_path()).write_bytes(binary)
        Path(self._version_path()).write_text(version)
        _LOGGER.info("Stored firmware v%s (%d bytes)", version, len(binary))

    def store_firmware_from_file(self, file_path: str, version: str) -> None:
        """Copy firmware binary from a file path and store version."""
        self._ensure_dir()
        shutil.copy2(file_path, self._bin_path())
        Path(self._version_path()).write_text(version)
        size = os.path.getsize(self._bin_path())
        _LOGGER.info("Stored firmware v%s from %s (%d bytes)", version, file_path, size)

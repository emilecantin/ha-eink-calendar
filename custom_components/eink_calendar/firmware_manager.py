"""Firmware binary management — serves the firmware bundled with the integration."""

from __future__ import annotations

import logging
import os
from typing import Tuple

_LOGGER = logging.getLogger(__name__)

FIRMWARE_FILENAME = "firmware.bin"
VERSION_FILENAME = "firmware.version"


class FirmwareManager:
    """Serve the firmware binary bundled alongside the integration."""

    def __init__(self, integration_dir: str) -> None:
        """Initialize with the integration's own directory."""
        self._integration_dir = integration_dir
        # Cache firmware info at init — version and binary don't change at runtime
        self._firmware_info = self._load_firmware_info()

    def _load_firmware_info(self) -> dict[str, str | int] | None:
        """Load firmware version and size from bundled files (called once at init)."""
        bin_path = os.path.join(self._integration_dir, FIRMWARE_FILENAME)
        version_path = os.path.join(self._integration_dir, VERSION_FILENAME)

        if not os.path.isfile(bin_path):
            return None

        try:
            with open(version_path) as f:
                version = f.read().strip()
        except Exception:
            return None

        if not version:
            return None

        size = os.path.getsize(bin_path)
        return {"version": version, "size": size}

    def get_firmware_info(self) -> dict[str, str | int] | None:
        """Get firmware version and size, or None if no firmware bundled."""
        return self._firmware_info

    def get_firmware_path(self) -> str | None:
        """Get path to firmware binary, or None if not bundled."""
        bin_path = os.path.join(self._integration_dir, FIRMWARE_FILENAME)
        if os.path.isfile(bin_path):
            return bin_path
        return None

    @staticmethod
    def _parse_version(version: str) -> Tuple[int, ...]:
        """Parse a semver string into a tuple of ints for comparison."""
        try:
            return tuple(int(x) for x in version.split("."))
        except (ValueError, AttributeError):
            return (0,)

    def build_ota_info(
        self, device_version: str, entry_id: str
    ) -> dict[str, str | int] | None:
        """Build OTA update info if bundled firmware is newer than device."""
        info = self._firmware_info
        if info is None:
            return None
        bundled = self._parse_version(info["version"])
        device = self._parse_version(device_version)
        if bundled <= device:
            return None
        return {
            "version": info["version"],
            "url": f"/api/eink_calendar/firmware/{entry_id}",
            "size": info["size"],
        }

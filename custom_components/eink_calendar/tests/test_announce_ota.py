"""Tests for OTA metadata in announce response."""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path so we can import firmware_manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from firmware_manager import FirmwareManager


def _make_integration_dir(tmpdir, version="1.0.0", firmware_data=None):
    """Create a fake integration directory with firmware.version and optional firmware.bin."""
    Path(os.path.join(tmpdir, "firmware.version")).write_text(version)
    if firmware_data is not None:
        Path(os.path.join(tmpdir, "firmware.bin")).write_bytes(firmware_data)


class TestAnnounceOtaMetadata:
    """Test that announce response includes firmware_update when update available."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_build_ota_info_when_update_available(self):
        """When bundled firmware version differs from device, OTA info should be present."""
        _make_integration_dir(self.tmpdir, "1.1.0", b"\x00" * 5000)
        manager = FirmwareManager(self.tmpdir)
        result = manager.build_ota_info("1.0.0", "test-entry-id")

        assert result is not None
        assert result["version"] == "1.1.0"
        assert result["url"] == "/api/eink_calendar/firmware/test-entry-id"
        assert result["size"] == 5000

    def test_no_ota_info_when_version_matches(self):
        """When device firmware matches bundled firmware, no OTA info."""
        _make_integration_dir(self.tmpdir, "1.0.0", b"\x00" * 5000)
        manager = FirmwareManager(self.tmpdir)
        result = manager.build_ota_info("1.0.0", "test-entry-id")

        assert result is None

    def test_no_ota_info_when_no_firmware_bundled(self):
        """When no firmware.bin is bundled, no OTA info."""
        _make_integration_dir(self.tmpdir, "1.0.0")
        manager = FirmwareManager(self.tmpdir)
        result = manager.build_ota_info("1.0.0", "test-entry-id")

        assert result is None

"""Tests for OTA metadata in announce response."""

import os
import sys
import tempfile

# Add parent directory to path so we can import firmware_manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from firmware_manager import FirmwareManager


class TestAnnounceOtaMetadata:
    """Test that announce response includes firmware_update when update available."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = FirmwareManager(self.tmpdir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_build_ota_info_when_update_available(self):
        """When firmware is stored and device version differs, OTA info should be present."""
        self.manager.store_firmware(b"\x00" * 5000, "1.1.0")
        result = self.manager.build_ota_info("1.0.0", "test-entry-id")

        assert result is not None
        assert result["version"] == "1.1.0"
        assert result["url"] == "/api/eink_calendar/firmware/test-entry-id"
        assert result["size"] == 5000

    def test_no_ota_info_when_version_matches(self):
        """When device firmware matches stored firmware, no OTA info."""
        self.manager.store_firmware(b"\x00" * 5000, "1.0.0")
        result = self.manager.build_ota_info("1.0.0", "test-entry-id")

        assert result is None

    def test_no_ota_info_when_no_firmware_stored(self):
        """When no firmware is stored, no OTA info."""
        result = self.manager.build_ota_info("1.0.0", "test-entry-id")

        assert result is None

"""Unit tests for firmware management module."""

import os
import tempfile
from pathlib import Path

from firmware_manager import FirmwareManager


def _make_integration_dir(tmpdir, version="1.0.0", firmware_data=None):
    """Create a fake integration directory with firmware.version and optional firmware.bin."""
    Path(os.path.join(tmpdir, "firmware.version")).write_text(version)
    if firmware_data is not None:
        Path(os.path.join(tmpdir, "firmware.bin")).write_bytes(firmware_data)


class TestFirmwareManager:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = FirmwareManager(self.tmpdir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_firmware_available(self):
        _make_integration_dir(self.tmpdir, "1.0.0")  # no firmware.bin
        info = self.manager.get_firmware_info()
        assert info is None

    def test_no_version_file(self):
        # firmware.bin exists but no firmware.version
        Path(os.path.join(self.tmpdir, "firmware.bin")).write_bytes(b"\x00")
        info = self.manager.get_firmware_info()
        assert info is None

    def test_firmware_available(self):
        binary = b"\x00" * 1024
        _make_integration_dir(self.tmpdir, "1.2.0", binary)
        info = self.manager.get_firmware_info()
        assert info is not None
        assert info["version"] == "1.2.0"
        assert info["size"] == 1024

    def test_get_firmware_path(self):
        binary = b"\x00" * 512
        _make_integration_dir(self.tmpdir, "1.0.0", binary)
        path = self.manager.get_firmware_path()
        assert path is not None
        assert Path(path).exists()
        assert Path(path).read_bytes() == binary

    def test_get_firmware_path_returns_none_when_missing(self):
        assert self.manager.get_firmware_path() is None

    def test_version_comes_from_manifest(self):
        _make_integration_dir(self.tmpdir, "2.0.0", b"\x01\x02")
        info = self.manager.get_firmware_info()
        assert info["version"] == "2.0.0"

    def test_build_ota_info_when_update_available(self):
        _make_integration_dir(self.tmpdir, "1.1.0", b"\x00" * 5000)
        ota = self.manager.build_ota_info("1.0.0", "entry123")
        assert ota is not None
        assert ota["version"] == "1.1.0"
        assert ota["size"] == 5000
        assert "entry123" in ota["url"]

    def test_no_ota_when_versions_match(self):
        _make_integration_dir(self.tmpdir, "1.0.0", b"\x00")
        ota = self.manager.build_ota_info("1.0.0", "entry123")
        assert ota is None

    def test_no_ota_when_no_firmware(self):
        _make_integration_dir(self.tmpdir, "1.0.0")  # no firmware.bin
        ota = self.manager.build_ota_info("1.0.0", "entry123")
        assert ota is None

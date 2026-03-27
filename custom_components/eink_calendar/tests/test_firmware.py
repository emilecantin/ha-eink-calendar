"""Unit tests for firmware management module."""

import os
import tempfile
from pathlib import Path

from firmware_manager import FirmwareManager


class TestFirmwareManager:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = FirmwareManager(self.tmpdir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_firmware_available(self):
        info = self.manager.get_firmware_info()
        assert info is None

    def test_firmware_available_after_store(self):
        binary = b"\x00" * 1024
        self.manager.store_firmware(binary, "1.2.0")
        info = self.manager.get_firmware_info()
        assert info is not None
        assert info["version"] == "1.2.0"
        assert info["size"] == 1024

    def test_get_firmware_path(self):
        binary = b"\x00" * 512
        self.manager.store_firmware(binary, "1.0.0")
        path = self.manager.get_firmware_path()
        assert path is not None
        assert Path(path).exists()
        assert Path(path).read_bytes() == binary

    def test_get_firmware_path_returns_none_when_missing(self):
        assert self.manager.get_firmware_path() is None

    def test_version_persists_in_sidecar(self):
        self.manager.store_firmware(b"\x01\x02", "2.0.0")
        # Create a new manager pointing to same dir — version should persist
        manager2 = FirmwareManager(self.tmpdir)
        info = manager2.get_firmware_info()
        assert info["version"] == "2.0.0"

    def test_store_overwrites_previous(self):
        self.manager.store_firmware(b"\x00" * 100, "1.0.0")
        self.manager.store_firmware(b"\xff" * 200, "1.1.0")
        info = self.manager.get_firmware_info()
        assert info["version"] == "1.1.0"
        assert info["size"] == 200
        assert self.manager.get_firmware_path() is not None
        assert Path(self.manager.get_firmware_path()).read_bytes() == b"\xff" * 200

    def test_needs_update_when_versions_differ(self):
        self.manager.store_firmware(b"\x00", "1.1.0")
        assert self.manager.needs_update("1.0.0") is True

    def test_no_update_when_versions_match(self):
        self.manager.store_firmware(b"\x00", "1.0.0")
        assert self.manager.needs_update("1.0.0") is False

    def test_no_update_when_no_firmware(self):
        assert self.manager.needs_update("1.0.0") is False

    def test_store_from_file(self):
        # Write a temp binary file
        src = os.path.join(self.tmpdir, "source.bin")
        with open(src, "wb") as f:
            f.write(b"\xde\xad\xbe\xef" * 100)
        self.manager.store_firmware_from_file(src, "3.0.0")
        info = self.manager.get_firmware_info()
        assert info["version"] == "3.0.0"
        assert info["size"] == 400

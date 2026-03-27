"""Tests for firmware version tracking and sensor."""

from unittest.mock import MagicMock

from custom_components.eink_calendar.const import (
    CONF_DEVICE_NAME,
    CONF_MAC_ADDRESS,
    DOMAIN,
    SENSOR_FIRMWARE_VERSION_NAME,
)
from custom_components.eink_calendar.coordinator import EinkCalendarDataCoordinator
from custom_components.eink_calendar.sensor import EinkCalendarFirmwareVersionSensor


def make_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    return hass


def make_entry(entry_id="test-entry-1", mac="AA:BB:CC:DD:EE:FF", name="Kitchen Calendar"):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {CONF_MAC_ADDRESS: mac, CONF_DEVICE_NAME: name}
    entry.options = {}
    return entry


def make_coordinator(hass=None, entry=None):
    hass = hass or make_hass()
    entry = entry or make_entry()
    return EinkCalendarDataCoordinator(hass, entry)


class TestCoordinatorFirmwareTracking:
    def test_firmware_version_defaults_to_unknown(self):
        """Coordinator should report 'unknown' before any device check-in."""
        coord = make_coordinator()
        assert coord.firmware_version == "unknown"

    def test_record_checkin_with_firmware_version(self):
        """record_checkin should store firmware version when provided."""
        coord = make_coordinator()
        coord.record_checkin(firmware_version="1.1.0")
        assert coord.firmware_version == "1.1.0"

    def test_record_checkin_without_firmware_version(self):
        """record_checkin without firmware_version should not change it."""
        coord = make_coordinator()
        coord.record_checkin(firmware_version="1.0.0")
        coord.record_checkin()  # No firmware version
        assert coord.firmware_version == "1.0.0"

    def test_firmware_version_updates(self):
        """Firmware version should update on subsequent check-ins."""
        coord = make_coordinator()
        coord.record_checkin(firmware_version="1.0.0")
        assert coord.firmware_version == "1.0.0"
        coord.record_checkin(firmware_version="1.1.0")
        assert coord.firmware_version == "1.1.0"

    def test_record_checkin_notifies_listeners(self):
        """Check-in with firmware version should notify listeners once."""
        coord = make_coordinator()
        callback = MagicMock()
        coord.async_add_listener(callback)
        coord.record_checkin(firmware_version="1.1.0")
        callback.assert_called_once()


class TestFirmwareVersionSensor:
    def test_sensor_name(self):
        """Sensor name should include device name."""
        entry = make_entry(name="Kitchen Calendar")
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarFirmwareVersionSensor(coord, entry)
        assert "Kitchen Calendar" in sensor.name
        assert "Firmware" in sensor.name

    def test_sensor_unique_id(self):
        """Sensor unique_id should use entry_id and sensor name constant."""
        entry = make_entry(entry_id="abc123")
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarFirmwareVersionSensor(coord, entry)
        assert sensor.unique_id == f"abc123_{SENSOR_FIRMWARE_VERSION_NAME}"

    def test_sensor_icon(self):
        """Sensor should use chip icon."""
        coord = make_coordinator()
        entry = make_entry()
        sensor = EinkCalendarFirmwareVersionSensor(coord, entry)
        assert sensor.icon == "mdi:chip"

    def test_sensor_value_default(self):
        """Sensor should return 'unknown' when no firmware version recorded."""
        coord = make_coordinator()
        entry = make_entry()
        sensor = EinkCalendarFirmwareVersionSensor(coord, entry)
        assert sensor.native_value == "unknown"

    def test_sensor_value_after_checkin(self):
        """Sensor should return firmware version after device reports it."""
        coord = make_coordinator()
        entry = make_entry()
        coord.record_checkin(firmware_version="1.1.0")
        sensor = EinkCalendarFirmwareVersionSensor(coord, entry)
        assert sensor.native_value == "1.1.0"

    def test_sensor_device_info_uses_mac(self):
        """Sensor device_info should use MAC as identifier."""
        entry = make_entry(mac="AA:BB:CC:DD:EE:FF")
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarFirmwareVersionSensor(coord, entry)
        identifiers = sensor.device_info["identifiers"]
        assert (DOMAIN, "AA:BB:CC:DD:EE:FF") in identifiers

    def test_sensor_device_info_fallback_to_entry_id(self):
        """Sensor should fall back to entry_id if no MAC."""
        entry = make_entry(mac="", entry_id="fallback-id")
        entry.data = {CONF_MAC_ADDRESS: "", CONF_DEVICE_NAME: "Test"}
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarFirmwareVersionSensor(coord, entry)
        identifiers = sensor.device_info["identifiers"]
        assert (DOMAIN, "fallback-id") in identifiers

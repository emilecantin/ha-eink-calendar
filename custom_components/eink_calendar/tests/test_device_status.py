"""Tests for device status state machine and sensors."""

from collections import deque
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from homeassistant.util import dt as dt_util

from custom_components.eink_calendar.const import (
    CONF_DEVICE_NAME,
    CONF_MAC_ADDRESS,
    CONF_REFRESH_INTERVAL,
    DOMAIN,
    SENSOR_CHECKIN_COUNT_NAME,
    SENSOR_DEVICE_ETAG_NAME,
    SENSOR_DEVICE_STATUS_NAME,
)
from custom_components.eink_calendar.coordinator import EinkCalendarDataCoordinator
from custom_components.eink_calendar.sensor import (
    EinkCalendarCheckinCountSensor,
    EinkCalendarDeviceEtagSensor,
    EinkCalendarDeviceStatusSensor,
)


def make_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    return hass


def make_entry(
    entry_id="test-entry-1",
    mac="AA:BB:CC:DD:EE:FF",
    name="Kitchen Calendar",
    refresh_interval=15,
):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {CONF_MAC_ADDRESS: mac, CONF_DEVICE_NAME: name}
    entry.options = {CONF_REFRESH_INTERVAL: refresh_interval}
    return entry


def make_coordinator(hass=None, entry=None):
    hass = hass or make_hass()
    entry = entry or make_entry()
    return EinkCalendarDataCoordinator(hass, entry)


class TestDeviceStatusStateMachine:
    def test_defaults_to_unknown(self):
        """Before any check-in, status is 'unknown'."""
        coord = make_coordinator()
        assert coord.device_status == "unknown"

    def test_healthy_after_normal_checkins(self):
        """After check-ins spaced at refresh_interval, status is 'healthy'."""
        coord = make_coordinator()
        now = dt_util.now()
        # 5 check-ins spaced 15 minutes apart
        for i in range(5):
            coord._checkin_timestamps.append(now - timedelta(minutes=15 * (4 - i)))
        coord.checkin_count = 5
        assert coord.device_status == "healthy"

    def test_rapid_checkin_detected(self):
        """10 check-ins 30s apart with 15min refresh_interval -> rapid_checkin."""
        coord = make_coordinator()
        now = dt_util.now()
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(seconds=30 * (9 - i)))
        coord.checkin_count = 10
        assert coord.device_status == "rapid_checkin"

    def test_rapid_checkin_not_cleared_by_single_normal_gap(self):
        """One long gap in the window doesn't reset rapid_checkin if median is still low."""
        coord = make_coordinator()
        now = dt_util.now()
        # 1 long gap followed by 9 short gaps (30s each)
        timestamps = deque(maxlen=10)
        base = now - timedelta(minutes=20)
        timestamps.append(base)
        # One normal gap of 15 minutes
        timestamps.append(base + timedelta(minutes=15))
        # Then 8 more at 30s intervals
        t = base + timedelta(minutes=15)
        for i in range(1, 9):
            timestamps.append(t + timedelta(seconds=30 * i))
        coord._checkin_timestamps = timestamps
        coord.checkin_count = 10
        # Median of [15*60, 30, 30, 30, 30, 30, 30, 30, 30] = 30s
        # 30 < 0.5 * 15 * 60 = 450 -> rapid
        assert coord.device_status == "rapid_checkin"

    def test_rapid_checkin_clears_after_sustained_normal_cadence(self):
        """Status returns to healthy when median interval recovers."""
        coord = make_coordinator()
        now = dt_util.now()
        # 10 check-ins at 15-minute intervals (normal cadence)
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(minutes=15 * (9 - i)))
        coord.checkin_count = 10
        assert coord.device_status == "healthy"

    def test_error_state_set_and_cleared(self):
        """record_device_error sets error, checkin clears it."""
        coord = make_coordinator()
        coord.record_checkin()
        assert coord.device_status == "healthy"
        coord.record_device_error("display timeout")
        assert coord.device_status == "error: display timeout"
        coord.record_checkin()
        assert coord.device_status == "healthy"

    def test_error_takes_priority_over_rapid_checkin(self):
        """Both error and rapid conditions -> error wins."""
        coord = make_coordinator()
        now = dt_util.now()
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(seconds=30 * (9 - i)))
        coord.checkin_count = 10
        coord.record_device_error("low battery")
        assert coord.device_status == "error: low battery"

    def test_checkin_count_increments(self):
        """Each record_checkin increments the counter."""
        coord = make_coordinator()
        assert coord.checkin_count == 0
        coord.record_checkin()
        assert coord.checkin_count == 1
        coord.record_checkin()
        assert coord.checkin_count == 2
        coord.record_checkin()
        assert coord.checkin_count == 3

    def test_device_etag_tracked(self):
        """device_etag field stores whatever is set."""
        coord = make_coordinator()
        assert coord.device_etag == "unknown"
        coord.device_etag = "abc123"
        assert coord.device_etag == "abc123"

    def test_overdue_detected(self):
        """evaluate_overdue flags overdue when last_checkin is too old."""
        coord = make_coordinator()
        # Set last_checkin to 31 minutes ago (> 2x 15min refresh)
        coord.last_checkin = dt_util.now() - timedelta(minutes=31)
        coord.checkin_count = 1
        coord._checkin_timestamps.append(coord.last_checkin)
        coord.evaluate_overdue()
        assert coord.device_status == "overdue"

    def test_overdue_clears_on_checkin(self):
        """Check-in clears overdue state."""
        coord = make_coordinator()
        coord.last_checkin = dt_util.now() - timedelta(minutes=31)
        coord.checkin_count = 1
        coord._checkin_timestamps.append(coord.last_checkin)
        coord.evaluate_overdue()
        assert coord.device_status == "overdue"
        coord.record_checkin()
        assert coord.device_status == "healthy"

    def test_single_checkin_is_healthy_not_rapid(self):
        """A single check-in should be healthy, not rapid (need >= 5 timestamps)."""
        coord = make_coordinator()
        coord.record_checkin()
        assert coord.device_status == "healthy"

    def test_updating_firmware_state(self):
        """record_firmware_update sets updating_firmware, check-in clears it."""
        coord = make_coordinator()
        coord.record_checkin()
        assert coord.device_status == "healthy"
        coord.record_firmware_update()
        assert coord.device_status == "updating_firmware"
        coord.record_checkin()
        assert coord.device_status == "healthy"

    def test_updating_firmware_not_overridden_by_overdue(self):
        """updating_firmware takes priority over overdue."""
        coord = make_coordinator()
        coord.record_checkin()
        coord.record_firmware_update()
        # Even if we evaluate overdue, updating_firmware wins
        coord._is_overdue = True
        assert coord.device_status == "updating_firmware"

    def test_error_overrides_updating_firmware(self):
        """Error takes priority over updating_firmware."""
        coord = make_coordinator()
        coord.record_firmware_update()
        coord.record_device_error("ota_failed")
        assert coord.device_status == "error: ota_failed"

    def test_error_reported_and_cleared_by_checkin(self):
        """Error reported via record_device_error clears on next checkin."""
        coord = make_coordinator()
        coord.record_checkin()
        assert coord.device_status == "healthy"
        coord.record_device_error("display_refresh_timeout")
        assert coord.device_status == "error: display_refresh_timeout"
        coord.record_checkin()
        assert coord.device_status == "healthy"

    def test_error_with_details(self):
        """Error message includes details when provided."""
        coord = make_coordinator()
        coord.record_device_error("download_failed: black_top HTTP 500")
        assert "download_failed" in coord.device_status


class TestDeviceStatusSensors:
    def test_status_sensor_name_and_unique_id(self):
        """Sensor name includes device name, unique_id uses entry_id."""
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)
        assert sensor.name == "Kitchen Calendar Device Status"
        assert sensor.unique_id == f"test-entry-1_{SENSOR_DEVICE_STATUS_NAME}"

    def test_status_sensor_value_reflects_coordinator(self):
        """Sensor value matches coordinator.device_status."""
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)
        assert sensor.native_value == "unknown"
        coord.record_checkin()
        assert sensor.native_value == "healthy"

    def test_status_sensor_icon_varies_by_state(self):
        """Icon changes based on status: healthy=check-circle, error=alert, rapid=speedometer, overdue=clock-alert."""
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)

        # Default unknown -> help-circle
        assert sensor.icon == "mdi:help-circle"

        # Healthy
        coord.record_checkin()
        assert sensor.icon == "mdi:check-circle"

        # Error
        coord.record_device_error("display timeout")
        assert sensor.icon == "mdi:alert"

        # Clear error, make rapid
        coord._device_error = None
        now = dt_util.now()
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(seconds=30 * (9 - i)))
        coord.checkin_count = 10
        assert sensor.icon == "mdi:speedometer"

        # Overdue
        coord._checkin_timestamps.clear()
        coord.checkin_count = 1
        coord.last_checkin = dt_util.now() - timedelta(minutes=31)
        coord._checkin_timestamps.append(coord.last_checkin)
        coord.evaluate_overdue()
        assert sensor.icon == "mdi:clock-alert"

    def test_etag_sensor_value(self):
        """ETag sensor shows coordinator.device_etag."""
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceEtagSensor(coord, entry)
        assert sensor.native_value == "unknown"
        coord.device_etag = "abc123"
        assert sensor.native_value == "abc123"

    def test_etag_sensor_name_and_unique_id(self):
        """ETag sensor has correct name and unique_id."""
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceEtagSensor(coord, entry)
        assert sensor.name == "Kitchen Calendar Device ETag"
        assert sensor.unique_id == f"test-entry-1_{SENSOR_DEVICE_ETAG_NAME}"

    def test_checkin_count_sensor_value(self):
        """Check-in count sensor shows coordinator.checkin_count."""
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarCheckinCountSensor(coord, entry)
        assert sensor.native_value == 0
        coord.record_checkin()
        assert sensor.native_value == 1
        coord.record_checkin()
        assert sensor.native_value == 2

    def test_checkin_count_sensor_name_and_unique_id(self):
        """Check-in count sensor has correct name and unique_id."""
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarCheckinCountSensor(coord, entry)
        assert sensor.name == "Kitchen Calendar Check-in Count"
        assert sensor.unique_id == f"test-entry-1_{SENSOR_CHECKIN_COUNT_NAME}"

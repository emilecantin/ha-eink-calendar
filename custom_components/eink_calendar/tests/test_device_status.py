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


class TestCheckinLog:
    def test_log_records_each_checkin(self):
        coord = make_coordinator()
        coord.record_checkin()
        coord.record_checkin()
        assert len(coord.checkin_log) == 2
        assert all("time" in entry for entry in coord.checkin_log)

    def test_first_entry_has_no_interval(self):
        """Nothing to measure against on the very first check-in."""
        coord = make_coordinator()
        coord.record_checkin()
        assert "interval_s" not in coord.checkin_log[0]

    def test_subsequent_entries_carry_interval(self):
        coord = make_coordinator()
        coord.record_checkin()
        coord.record_checkin()
        assert "interval_s" in coord.checkin_log[1]

    def test_diagnostics_merged_into_log_entry(self):
        coord = make_coordinator()
        coord.record_checkin(
            diagnostics={"reset_reason": "brownout", "last_stage": "display_sent"}
        )
        entry = coord.checkin_log[0]
        assert entry["reset_reason"] == "brownout"
        assert entry["last_stage"] == "display_sent"

    def test_log_is_bounded(self):
        """A device in a reboot loop must not grow state without limit."""
        coord = make_coordinator()
        for _ in range(50):
            coord.record_checkin()
        assert len(coord.checkin_log) == 20

    def test_last_diagnostics_preserved_when_omitted(self):
        """A check-in without diagnostics shouldn't wipe the previous ones."""
        coord = make_coordinator()
        coord.record_checkin(diagnostics={"reset_reason": "panic"})
        coord.record_checkin()
        assert coord.last_diagnostics == {"reset_reason": "panic"}


class TestErrorRetention:
    def test_last_error_survives_next_checkin(self):
        """The reboot-loop evidence must outlive the reboot that follows it."""
        coord = make_coordinator()
        coord.record_device_error("littlefs_read_failed: /rd1.bin")
        coord.record_checkin()

        # Current status clears, as before...
        assert coord.device_status == "healthy"
        # ...but the evidence remains
        assert coord.last_error == "littlefs_read_failed: /rd1.bin"
        assert coord.last_error_time is not None

    def test_last_error_starts_empty(self):
        coord = make_coordinator()
        assert coord.last_error is None
        assert coord.last_error_time is None


class TestIntervalProperties:
    def test_median_none_below_threshold(self):
        coord = make_coordinator()
        for _ in range(4):
            coord.record_checkin()
        assert coord.median_checkin_interval is None

    def test_median_computed_from_timestamps(self):
        coord = make_coordinator()
        now = dt_util.now()
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(seconds=30 * (9 - i)))
        assert coord.median_checkin_interval == 30

    def test_expected_interval_from_options(self):
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        assert coord.expected_checkin_interval == 900


class TestDiagnosis:
    def test_healthy_device(self):
        coord = make_coordinator()
        coord.record_checkin(diagnostics={"reset_reason": "deepsleep"})
        assert "on schedule" in coord.diagnosis

    def test_brownout_surfaced(self):
        coord = make_coordinator()
        coord.record_checkin(
            diagnostics={"reset_reason": "brownout", "last_stage": "display_sent"}
        )
        assert "brownout" in coord.diagnosis

    def test_rapid_clean_reboot_explained(self):
        """The target scenario: fast check-ins, clean wakes, no screen write."""
        coord = make_coordinator()
        now = dt_util.now()
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(seconds=30 * (9 - i)))
        coord.checkin_count = 10
        coord.last_diagnostics = {
            "reset_reason": "deepsleep",
            "last_stage": "downloaded",
        }
        assert coord.device_status == "rapid_checkin"
        assert "ETag" in coord.diagnosis

    def test_no_diagnostics_does_not_raise(self):
        """Firmware older than 1.3.0 sends nothing."""
        coord = make_coordinator()
        coord.record_checkin()
        assert isinstance(coord.diagnosis, str)


class TestDeviceStatusAttributes:
    def test_attributes_expose_diagnostics(self):
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)
        coord.record_checkin(
            diagnostics={
                "reset_reason": "brownout",
                "last_stage": "display_sent",
                "boot_count": 7,
                "free_heap": 1234,
            }
        )

        attrs = sensor.extra_state_attributes
        assert attrs["reset_reason"] == "brownout"
        assert attrs["last_stage"] == "display_sent"
        assert attrs["boot_count"] == 7
        assert attrs["free_heap"] == 1234
        assert attrs["expected_checkin_interval_s"] == 900
        assert "brownout" in attrs["diagnosis"]
        assert len(attrs["recent_checkins"]) == 1

    def test_attributes_include_retained_error(self):
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)
        coord.record_device_error("littlefs_read_failed: /rd1.bin")
        coord.record_checkin()

        attrs = sensor.extra_state_attributes
        assert attrs["last_error"] == "littlefs_read_failed: /rd1.bin"
        assert attrs["last_error_time"] is not None

    def test_attributes_safe_with_no_data(self):
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)

        attrs = sensor.extra_state_attributes
        assert attrs["reset_reason"] is None
        assert attrs["last_error"] is None
        assert attrs["recent_checkins"] == []

    def test_recent_checkins_capped_at_ten(self):
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)
        for _ in range(20):
            coord.record_checkin()
        assert len(sensor.extra_state_attributes["recent_checkins"]) == 10


class TestFingerprintTracking:
    def test_check_result_annotates_last_entry(self):
        coord = make_coordinator()
        coord.record_checkin(diagnostics={"device_etag": "abc"})
        coord.record_check_result(server_etag="def", image_changed=True)

        entry = coord.checkin_log[-1]
        assert entry["device_etag"] == "abc"
        assert entry["server_etag"] == "def"
        assert entry["etag_match"] is False
        assert coord.server_etag == "def"

    def test_match_recorded_when_unchanged(self):
        coord = make_coordinator()
        coord.record_checkin(diagnostics={"device_etag": "abc"})
        coord.record_check_result(server_etag="abc", image_changed=False)
        assert coord.checkin_log[-1]["etag_match"] is True

    def test_check_result_without_prior_checkin_does_not_raise(self):
        coord = make_coordinator()
        coord.record_check_result(server_etag="def", image_changed=True)
        assert coord.server_etag == "def"
        assert coord.checkin_log == []

    def test_stuck_fingerprint_detected_through_coordinator(self):
        coord = make_coordinator()
        for _ in range(3):
            coord.record_checkin(diagnostics={"device_etag": "abc"})
            coord.record_check_result(server_etag="def", image_changed=True)
        assert coord.fingerprint_stuck is True

    def test_advancing_fingerprint_not_stuck(self):
        coord = make_coordinator()
        for tag in ("abc", "def", "ghi"):
            coord.record_checkin(diagnostics={"device_etag": tag})
            coord.record_check_result(server_etag="zzz", image_changed=True)
        assert coord.fingerprint_stuck is False

    def test_diagnosis_names_both_fingerprints(self):
        coord = make_coordinator()
        coord.device_etag = "abc"
        for _ in range(3):
            coord.record_checkin(
                diagnostics={"device_etag": "abc", "display_valid": False}
            )
            coord.record_check_result(server_etag="def", image_changed=True)

        diagnosis = coord.diagnosis
        assert "abc" in diagnosis
        assert "def" in diagnosis
        assert "never completed a refresh" in diagnosis

    def test_server_etag_defaults_to_unknown(self):
        coord = make_coordinator()
        assert coord.server_etag == "unknown"

    def test_attributes_expose_fingerprints(self):
        entry = make_entry()
        coord = make_coordinator(entry=entry)
        sensor = EinkCalendarDeviceStatusSensor(coord, entry)
        coord.device_etag = "abc"
        coord.record_checkin(diagnostics={"device_etag": "abc", "display_valid": True})
        coord.record_check_result(server_etag="def", image_changed=True)

        attrs = sensor.extra_state_attributes
        assert attrs["device_etag"] == "abc"
        assert attrs["server_etag"] == "def"
        assert attrs["display_valid"] is True
        assert attrs["fingerprint_stuck"] is False


class TestCommandedIntervalTracking:
    """Health detectors must judge against what HA actually commanded.

    Once quiet hours vary the interval, comparing observed gaps to the static
    config option produces false diagnoses in both directions: a long quiet
    interval looks 'overdue', and returning to the short daytime interval
    looks like 'rapid_checkin'.
    """

    def test_base_interval_seeds_from_options(self):
        coord = make_coordinator(entry=make_entry(refresh_interval=20))
        assert coord.base_interval_minutes == 20

    def test_base_interval_is_settable(self):
        coord = make_coordinator(entry=make_entry(refresh_interval=20))
        coord.base_interval_minutes = 45
        assert coord.base_interval_minutes == 45

    def test_expected_interval_follows_commanded_value(self):
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        coord.record_commanded_interval(120)
        assert coord.expected_checkin_interval == 120 * 60

    def test_expected_interval_falls_back_to_option(self):
        """Before anything is commanded, the stored option still applies."""
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        assert coord.expected_checkin_interval == 15 * 60

    def test_quiet_hours_interval_is_not_overdue(self):
        """A device correctly sleeping 2h must not be flagged overdue."""
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        coord.record_commanded_interval(120)
        coord.last_checkin = dt_util.now() - timedelta(minutes=90)
        coord.evaluate_overdue()
        assert coord._is_overdue is False

    def test_still_overdue_past_twice_the_commanded_interval(self):
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        coord.record_commanded_interval(120)
        coord.last_checkin = dt_util.now() - timedelta(minutes=260)
        coord.evaluate_overdue()
        assert coord._is_overdue is True

    def test_short_option_does_not_make_a_quiet_device_overdue(self):
        """The regression this fixes: 15min option, 2h commanded, 90min elapsed."""
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        coord.last_checkin = dt_util.now() - timedelta(minutes=90)
        coord.record_commanded_interval(120)
        coord.evaluate_overdue()
        assert coord._is_overdue is False

    def test_genuine_reboot_loop_still_detected_during_quiet_hours(self):
        """A 30s loop is still rapid even when a 2h interval was commanded."""
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        coord.record_commanded_interval(120)
        now = dt_util.now()
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(seconds=30 * (9 - i)))
        coord.checkin_count = 10
        assert coord.device_status == "rapid_checkin"

    def test_daytime_cadence_after_quiet_hours_is_healthy(self):
        """Returning to a 15min cadence must not read as rapid vs a 2h expectation."""
        coord = make_coordinator(entry=make_entry(refresh_interval=15))
        coord.record_commanded_interval(15)
        now = dt_util.now()
        for i in range(10):
            coord._checkin_timestamps.append(now - timedelta(minutes=15 * (9 - i)))
        coord.checkin_count = 10
        assert coord.device_status == "healthy"

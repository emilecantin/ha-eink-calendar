"""Tests for boot diagnostics interpretation."""

from custom_components.eink_calendar.device_diagnostics import (
    is_fingerprint_stuck,
    BOOT_STAGES,
    diagnose,
    stage_index,
)


class TestStageIndex:
    def test_known_stages_are_ordered(self):
        assert stage_index("boot") < stage_index("checked")
        assert stage_index("checked") < stage_index("display_sent")
        assert stage_index("display_sent") < stage_index("display_refreshed")

    def test_unknown_stage_is_negative(self):
        assert stage_index("nonsense") == -1
        assert stage_index(None) == -1

    def test_firmware_contract_stages_present(self):
        """These names come from diag_stage_name() in diagnostics.h."""
        assert BOOT_STAGES[0] == "boot"
        assert BOOT_STAGES[-1] == "sleeping"
        assert "display_refreshed" in BOOT_STAGES


class TestFaultResets:
    def test_brownout_names_the_power_supply(self):
        result = diagnose(
            reset_reason="brownout", last_stage="display_sent", is_rapid=True
        )
        assert "brownout" in result
        assert "supply voltage" in result
        assert "display_sent" in result

    def test_watchdog_reported(self):
        result = diagnose(
            reset_reason="task_wdt", last_stage="display_init", is_rapid=True
        )
        assert "task_wdt" in result
        assert "watchdog" in result

    def test_panic_reported(self):
        result = diagnose(reset_reason="panic", last_stage="downloaded")
        assert "crashed" in result

    def test_fault_reported_even_when_not_yet_rapid(self):
        """A brownout matters immediately, before 5 check-ins accumulate."""
        result = diagnose(
            reset_reason="brownout", last_stage="display_sent", is_rapid=False
        )
        assert "brownout" in result


class TestHealthy:
    def test_normal_cadence(self):
        result = diagnose(
            reset_reason="deepsleep", last_stage="sleeping", is_rapid=False
        )
        assert result == "Device is checking in on schedule."

    def test_normal_cadence_but_prior_error_mentioned(self):
        result = diagnose(
            reset_reason="deepsleep",
            last_stage="sleeping",
            is_rapid=False,
            last_error="download_failed: /black_top",
        )
        assert "on schedule" in result
        assert "download_failed" in result


class TestRapidCleanReboot:
    def test_incomplete_refresh_explains_etag_loop(self):
        """The silent phase-2 failure: clean wake, but never reached refresh."""
        result = diagnose(
            reset_reason="deepsleep",
            last_stage="downloaded",
            is_rapid=True,
            median_interval=60.0,
            expected_interval=900.0,
        )
        assert "downloaded" in result
        assert "ETag" in result
        assert "60s" in result
        assert "900s" in result

    def test_last_error_takes_the_lead_when_present(self):
        result = diagnose(
            reset_reason="deepsleep",
            last_stage="downloaded",
            is_rapid=True,
            last_error="littlefs_read_failed: /rd1.bin",
        )
        assert "littlefs_read_failed" in result

    def test_rapid_after_full_refresh_has_no_false_alarm(self):
        """Reached the end of the cycle — don't claim the refresh failed."""
        result = diagnose(
            reset_reason="deepsleep",
            last_stage="sleeping",
            is_rapid=True,
            median_interval=30.0,
            expected_interval=900.0,
        )
        assert "ETag" not in result
        assert "sleeping" in result

    def test_cadence_omitted_when_intervals_unknown(self):
        result = diagnose(
            reset_reason="deepsleep", last_stage="checked", is_rapid=True
        )
        assert "versus an expected" not in result


class TestMissingData:
    def test_no_diagnostics_at_all(self):
        """Firmware older than 1.3.0 sends nothing — must not raise."""
        result = diagnose()
        assert isinstance(result, str)
        assert result

    def test_rapid_with_no_diagnostics(self):
        result = diagnose(is_rapid=True)
        assert isinstance(result, str)
        assert result


class TestFingerprintStuck:
    def _entry(self, device_etag, etag_match):
        return {"device_etag": device_etag, "etag_match": etag_match}

    def test_same_etag_never_matching_is_stuck(self):
        """The device re-downloads but never persists the new fingerprint."""
        log = [self._entry("abc", False) for _ in range(3)]
        assert is_fingerprint_stuck(log) is True

    def test_below_threshold_is_not_stuck(self):
        log = [self._entry("abc", False) for _ in range(2)]
        assert is_fingerprint_stuck(log) is False

    def test_any_recent_match_clears_it(self):
        log = [
            self._entry("abc", False),
            self._entry("abc", True),
            self._entry("abc", False),
        ]
        assert is_fingerprint_stuck(log) is False

    def test_advancing_etag_is_not_stuck(self):
        """Fingerprint changing means the device IS persisting refreshes."""
        log = [
            self._entry("abc", False),
            self._entry("def", False),
            self._entry("ghi", False),
        ]
        assert is_fingerprint_stuck(log) is False

    def test_only_recent_entries_considered(self):
        """Old healthy history shouldn't mask a current stuck loop."""
        log = [self._entry("old", True) for _ in range(5)]
        log += [self._entry("abc", False) for _ in range(3)]
        assert is_fingerprint_stuck(log) is True

    def test_entries_without_outcome_are_skipped(self):
        """Older firmware / checks that errored before render lack etag_match."""
        log = [{"time": "t"} for _ in range(5)]
        assert is_fingerprint_stuck(log) is False

    def test_missing_device_etag_is_skipped(self):
        """A device sending no fingerprint at all isn't 'stuck' on one."""
        log = [self._entry(None, False) for _ in range(3)]
        assert is_fingerprint_stuck(log) is False

    def test_empty_log(self):
        assert is_fingerprint_stuck([]) is False


class TestFingerprintInDiagnosis:
    def test_stuck_fingerprint_named_in_rapid_loop(self):
        result = diagnose(
            reset_reason="deepsleep",
            last_stage="downloaded",
            is_rapid=True,
            fingerprint_stuck=True,
            device_etag="abc123",
            server_etag="def456",
        )
        assert "abc123" in result
        assert "def456" in result
        assert "never being stored" in result

    def test_stuck_fingerprint_surfaced_even_at_normal_cadence(self):
        """Screen frozen without a reboot loop is still worth reporting."""
        result = diagnose(
            reset_reason="deepsleep",
            last_stage="sleeping",
            is_rapid=False,
            fingerprint_stuck=True,
            device_etag="abc123",
            server_etag="def456",
        )
        assert "display is not updating" in result
        assert "abc123" in result

    def test_never_refreshed_called_out(self):
        result = diagnose(
            fingerprint_stuck=True,
            device_etag="abc123",
            server_etag="def456",
            display_valid=False,
        )
        assert "never completed a refresh" in result

    def test_display_valid_true_omits_never_claim(self):
        result = diagnose(
            fingerprint_stuck=True,
            device_etag="abc123",
            server_etag="def456",
            display_valid=True,
        )
        assert "never completed a refresh" not in result

    def test_fingerprint_appended_to_brownout(self):
        result = diagnose(
            reset_reason="brownout",
            last_stage="display_sent",
            fingerprint_stuck=True,
            device_etag="abc123",
            server_etag="def456",
        )
        assert "brownout" in result
        assert "abc123" in result

"""Tests for HTTP view security hardening (GitHub issue #2).

Tests:
1. Exception in announce handler returns generic message, not exception text
2. Exception in bitmap handler returns generic message, not exception text
3. _recent_announces entries are cleaned up after cooldown period
4. Manual entry (no MAC) allows requests through
"""

import asyncio
import json
import sys
import time
from unittest.mock import AsyncMock, MagicMock


# --- Patching infrastructure ---
# conftest.py mocks aiohttp/homeassistant, so we need to set up real-enough
# fakes for HomeAssistantView and web.Response before importing http_views.

class _FakeResponse:
    """Stand-in for aiohttp.web.Response that captures args."""

    def __init__(self, *, text=None, body=None, status=200, content_type=None, headers=None):
        self.text = text
        self.body = body
        self.status = status
        self.content_type = content_type
        self.headers = headers or {}


class _FakeHomeAssistantView:
    """Minimal stand-in for HomeAssistantView."""

    requires_auth = True

    def json(self, data, status_code=200):
        return _FakeResponse(
            text=json.dumps(data),
            content_type="application/json",
            status=status_code,
        )


# Patch before importing http_views
sys.modules["homeassistant.components.http"].HomeAssistantView = _FakeHomeAssistantView

# We need web.Response to be our _FakeResponse. http_views uses `from aiohttp import web`
# then calls `web.Response(...)`. The mock aiohttp module's `.web` is a MagicMock attribute,
# so we set `.web.Response` to our fake.
sys.modules["aiohttp"].web.Response = _FakeResponse

# Force reimport of http_views
_key = "custom_components.eink_calendar.http_views"
if _key in sys.modules:
    del sys.modules[_key]

from custom_components.eink_calendar.http_views import (
    EinkCalendarAnnounceView,
    EinkCalendarBitmapView,
    _parse_diagnostics,
)


def _make_hass():
    """Create a minimal mock hass object."""
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = []
    hass.config_entries.flow.async_progress.return_value = []
    hass.config_entries.flow.async_init = AsyncMock()
    hass.data = {}
    return hass


def _make_request(body=None, headers=None):
    """Create a mock aiohttp request."""
    req = MagicMock()
    if body is not None:
        req.json = AsyncMock(return_value=body)
    else:
        req.json = AsyncMock(side_effect=Exception("No body"))
    req.headers = headers or {}
    req.remote = "192.168.1.100"
    return req


def _run(coro):
    """Run an async coroutine."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestAnnounceErrorLeak:
    """Exception in announce handler must return generic message, not str(err)."""

    def test_announce_exception_returns_generic_message(self):
        """When announce handler raises, response must NOT contain exception details."""
        hass = _make_hass()
        view = EinkCalendarAnnounceView(hass)

        # Make request.json() raise an exception with sensitive info
        req = MagicMock()
        req.json = AsyncMock(
            side_effect=Exception("/home/user/.config/secrets: permission denied")
        )
        req.remote = "192.168.1.100"

        resp = _run(view.post(req))

        # The response body must NOT contain the exception string
        resp_data = json.loads(resp.text)
        assert "secrets" not in resp_data.get("message", "")
        assert "permission" not in resp_data.get("message", "")
        assert resp_data["status"] == "error"
        assert resp.status == 500


class TestBitmapErrorLeak:
    """Exception in bitmap handler must return generic message, not str(err)."""

    def test_bitmap_exception_returns_generic_message(self):
        """When bitmap handler raises, response text must NOT contain exception details."""
        hass = _make_hass()
        view = EinkCalendarBitmapView(hass)

        # Make async_get_entry raise with sensitive info
        hass.config_entries.async_get_entry.side_effect = Exception(
            "database error at /var/lib/ha/db.sqlite3"
        )

        req = _make_request(headers={"X-MAC": "AA:BB:CC:DD:EE:FF"})

        resp = _run(view.get(req, entry_id="test-entry", layer="black_top"))

        # The response text must NOT contain the exception string
        assert resp.status == 500
        assert "db.sqlite3" not in resp.text
        assert "database error" not in resp.text


class TestRecentAnnouncesCleanup:
    """_recent_announces dict must evict entries older than ANNOUNCE_COOLDOWN."""

    def test_stale_entries_are_cleaned_up(self):
        """After cooldown, old MAC entries should be removed from _recent_announces."""
        hass = _make_hass()
        view = EinkCalendarAnnounceView(hass)

        # Manually inject some old entries
        now = time.monotonic()
        view._recent_announces["AA:BB:CC:DD:EE:01"] = now - 200  # old
        view._recent_announces["AA:BB:CC:DD:EE:02"] = now - 200  # old
        view._recent_announces["AA:BB:CC:DD:EE:03"] = now - 10   # recent

        # Make a valid announce request that triggers cleanup
        req = _make_request(body={
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Test",
            "firmware_version": "1.0.0",
        })

        _run(view.post(req))

        # Old entries should have been evicted
        assert "AA:BB:CC:DD:EE:01" not in view._recent_announces
        assert "AA:BB:CC:DD:EE:02" not in view._recent_announces
        # Recent entry should still be there
        assert "AA:BB:CC:DD:EE:03" in view._recent_announces

    def test_many_unique_macs_dont_accumulate(self):
        """Entries older than cooldown are cleaned up even with many MACs."""
        hass = _make_hass()
        view = EinkCalendarAnnounceView(hass)

        # Inject 100 old entries
        now = time.monotonic()
        for i in range(100):
            mac = f"AA:BB:CC:DD:{i:02X}:00"
            view._recent_announces[mac] = now - 200  # all old

        # Make a request
        req = _make_request(body={
            "mac": "FF:FF:FF:FF:FF:FF",
            "name": "Test",
            "firmware_version": "1.0.0",
        })

        _run(view.post(req))

        # All old entries should be gone, only the new one (and maybe FF:FF...)
        assert len(view._recent_announces) <= 2


class TestManualEntryMacBypass:
    """Manual entries (no MAC configured) should allow requests through."""

    def test_no_mac_entry_allows_request(self):
        """When entry has no MAC, bitmap requests should succeed."""
        hass = _make_hass()
        view = EinkCalendarBitmapView(hass)

        # Create a config entry with no MAC (manual entry)
        entry = MagicMock()
        entry.domain = "eink_calendar"
        entry.data = {}  # No CONF_MAC_ADDRESS
        entry.options = {"refresh_interval": 15}
        entry.entry_id = "manual-entry-123"
        hass.config_entries.async_get_entry.return_value = entry

        # Create coordinator with rendered data
        coordinator = MagicMock()
        rendered = MagicMock()
        rendered.etag = '"abc123"'
        rendered.get_black_top.return_value = b"\x00" * 100
        coordinator.async_get_rendered = AsyncMock(return_value=rendered)
        coordinator.last_update_success = True
        hass.data["eink_calendar"] = {"manual-entry-123": coordinator}

        # Request without X-MAC header
        req = _make_request(headers={})

        resp = _run(view.get(req, entry_id="manual-entry-123", layer="black_top"))

        # Should succeed (200) not be rejected
        assert resp.status == 200


class TestBootDiagnosticsHeaders:
    """ESP32 boot diagnostics arrive as headers on the /check request.

    They are unauthenticated device input, so parsing must never raise, and
    must degrade gracefully for firmware older than 1.3.0 that omits them.
    """

    def test_parses_full_diagnostics(self):
        req = _make_request(headers={
            "X-Reset-Reason": "brownout",
            "X-Last-Stage": "display_sent",
            "X-Boot-Count": "42",
            "X-Free-Heap": "123456",
            "X-Last-Sleep": "60",
        })

        assert _parse_diagnostics(req) == {
            "reset_reason": "brownout",
            "last_stage": "display_sent",
            "boot_count": 42,
            "free_heap": 123456,
            "last_sleep_s": 60,
            "device_etag": None,
        }

    def test_missing_headers_yield_only_null_fingerprint(self):
        """Firmware < 1.3.0 sends none of these; device_etag is always recorded."""
        assert _parse_diagnostics(_make_request(headers={})) == {"device_etag": None}

    def test_malformed_numeric_headers_are_dropped(self):
        req = _make_request(headers={
            "X-Reset-Reason": "panic",
            "X-Boot-Count": "not-a-number",
            "X-Free-Heap": "",
        })

        result = _parse_diagnostics(req)
        assert result == {"reset_reason": "panic", "device_etag": None}

    def test_oversized_strings_are_capped(self):
        req = _make_request(headers={"X-Reset-Reason": "x" * 500})
        assert len(_parse_diagnostics(req)["reset_reason"]) == 32

    def test_whitespace_only_headers_ignored(self):
        req = _make_request(headers={"X-Last-Stage": "   "})
        assert _parse_diagnostics(req) == {"device_etag": None}

    def test_check_passes_diagnostics_to_coordinator(self):
        """End-to-end: headers on /check reach record_checkin()."""
        hass = _make_hass()
        view = EinkCalendarBitmapView(hass)

        entry = MagicMock()
        entry.domain = "eink_calendar"
        entry.data = {"mac_address": "AA:BB:CC:DD:EE:FF"}
        entry.options = {"refresh_interval": 15}
        entry.entry_id = "entry-1"
        hass.config_entries.async_get_entry.return_value = entry

        coordinator = MagicMock()
        rendered = MagicMock()
        rendered.etag = '"abc123"'
        coordinator.async_get_rendered = AsyncMock(return_value=rendered)
        coordinator.async_request_refresh = AsyncMock()
        coordinator.last_update_success = True
        coordinator.consume_force_refresh.return_value = False
        coordinator.last_diagnostics = {}
        hass.data["eink_calendar"] = {"entry-1": coordinator}

        req = _make_request(headers={
            "X-MAC": "AA:BB:CC:DD:EE:FF",
            "X-Firmware-Version": "1.3.0",
            "X-Reset-Reason": "brownout",
            "X-Last-Stage": "display_sent",
            "X-Boot-Count": "7",
        })

        _run(view.get(req, entry_id="entry-1", layer="check"))

        coordinator.record_checkin.assert_called_once_with(
            firmware_version="1.3.0",
            diagnostics={
                "reset_reason": "brownout",
                "last_stage": "display_sent",
                "boot_count": 7,
                "device_etag": None,
            },
        )


class TestFingerprintHeaders:
    """The device's fingerprint (If-None-Match) must be recorded on every check."""

    def test_if_none_match_captured_as_device_etag(self):
        req = _make_request(headers={"If-None-Match": '"abc123"'})
        assert _parse_diagnostics(req)["device_etag"] == '"abc123"'

    def test_absent_fingerprint_recorded_as_none(self):
        """A device with no stored ETag must be distinguishable from 'unchanged'."""
        assert _parse_diagnostics(_make_request(headers={}))["device_etag"] is None

    def test_oversized_fingerprint_capped(self):
        req = _make_request(headers={"If-None-Match": "x" * 500})
        assert len(_parse_diagnostics(req)["device_etag"]) == 64

    def test_display_valid_parsed_as_bool(self):
        assert _parse_diagnostics(
            _make_request(headers={"X-Display-Valid": "1"})
        )["display_valid"] is True
        assert _parse_diagnostics(
            _make_request(headers={"X-Display-Valid": "0"})
        )["display_valid"] is False

    def test_malformed_display_valid_dropped(self):
        req = _make_request(headers={"X-Display-Valid": "maybe"})
        assert "display_valid" not in _parse_diagnostics(req)

    def test_check_records_result_with_server_etag(self):
        """The server ETag is attached after the render completes."""
        hass = _make_hass()
        view = EinkCalendarBitmapView(hass)

        entry = MagicMock()
        entry.domain = "eink_calendar"
        entry.data = {"mac_address": "AA:BB:CC:DD:EE:FF"}
        entry.options = {"refresh_interval": 15}
        entry.entry_id = "entry-1"
        hass.config_entries.async_get_entry.return_value = entry

        coordinator = MagicMock()
        rendered = MagicMock()
        rendered.etag = '"server999"'
        coordinator.async_get_rendered = AsyncMock(return_value=rendered)
        coordinator.async_request_refresh = AsyncMock()
        coordinator.last_update_success = True
        coordinator.consume_force_refresh.return_value = False
        coordinator.last_diagnostics = {}
        hass.data["eink_calendar"] = {"entry-1": coordinator}

        req = _make_request(headers={
            "X-MAC": "AA:BB:CC:DD:EE:FF",
            "If-None-Match": '"device111"',
        })

        _run(view.get(req, entry_id="entry-1", layer="check"))

        coordinator.record_check_result.assert_called_once_with(
            server_etag='"server999"', image_changed=True
        )
        assert coordinator.device_etag == '"device111"'

    def test_no_fingerprint_recorded_as_none_marker(self):
        """device_etag must not retain a stale value when none is sent."""
        hass = _make_hass()
        view = EinkCalendarBitmapView(hass)

        entry = MagicMock()
        entry.domain = "eink_calendar"
        entry.data = {}
        entry.options = {"refresh_interval": 15}
        entry.entry_id = "entry-1"
        hass.config_entries.async_get_entry.return_value = entry

        coordinator = MagicMock()
        rendered = MagicMock()
        rendered.etag = '"server999"'
        coordinator.async_get_rendered = AsyncMock(return_value=rendered)
        coordinator.async_request_refresh = AsyncMock()
        coordinator.last_update_success = True
        coordinator.consume_force_refresh.return_value = False
        coordinator.last_diagnostics = {}
        hass.data["eink_calendar"] = {"entry-1": coordinator}

        _run(view.get(_make_request(headers={}), entry_id="entry-1", layer="check"))

        assert coordinator.device_etag == "(none)"


class TestDynamicRefreshInterval:
    """HA commands the sleep interval on every check-in, quiet hours included."""

    @staticmethod
    def _setup(options, etag_match):
        hass = _make_hass()
        view = EinkCalendarBitmapView(hass)

        entry = MagicMock()
        entry.domain = "eink_calendar"
        entry.data = {"mac_address": "AA:BB:CC:DD:EE:FF"}
        entry.options = options
        entry.entry_id = "entry-1"
        hass.config_entries.async_get_entry.return_value = entry

        coordinator = MagicMock()
        rendered = MagicMock()
        rendered.etag = '"abc123"'
        coordinator.async_get_rendered = AsyncMock(return_value=rendered)
        coordinator.async_request_refresh = AsyncMock()
        coordinator.last_update_success = True
        coordinator.consume_force_refresh.return_value = False
        coordinator.last_diagnostics = {}
        coordinator.base_interval_minutes = options.get("refresh_interval", 15)
        hass.data["eink_calendar"] = {"entry-1": coordinator}

        headers = {"X-MAC": "AA:BB:CC:DD:EE:FF"}
        if etag_match:
            headers["If-None-Match"] = '"abc123"'
        req = _make_request(headers=headers)
        return view, req, coordinator

    @staticmethod
    def _at(hour):
        from datetime import datetime as _dt
        return _dt(2026, 8, 30, hour, 0)

    QUIET = {
        "refresh_interval": 15,
        "quiet_start": "23:00:00",
        "quiet_end": "07:00:00",
        "quiet_multiplier": 8,
    }

    def _run_check(self, options, hour, etag_match):
        import custom_components.eink_calendar.http_views as hv
        from unittest.mock import patch

        view, req, coordinator = self._setup(options, etag_match)
        with patch.object(hv.dt_util, "now", return_value=self._at(hour)):
            resp = _run(view.get(req, entry_id="entry-1", layer="check"))
        return resp, coordinator

    def test_304_header_reflects_quiet_hours(self):
        resp, _ = self._run_check(self.QUIET, hour=2, etag_match=True)
        assert resp.status == 304
        assert resp.headers["X-Refresh-Interval"] == "120"

    def test_304_header_outside_quiet_hours_is_base(self):
        resp, _ = self._run_check(self.QUIET, hour=12, etag_match=True)
        assert resp.status == 304
        assert resp.headers["X-Refresh-Interval"] == "15"

    def test_200_body_reflects_quiet_hours(self):
        resp, _ = self._run_check(self.QUIET, hour=2, etag_match=False)
        assert resp.status == 200
        assert json.loads(resp.text)["refresh_interval"] == 120

    def test_both_paths_agree_at_the_same_clock_time(self):
        """The 304 header and the 200 body must never disagree."""
        for hour in (2, 12, 23):
            r304, _ = self._run_check(self.QUIET, hour=hour, etag_match=True)
            r200, _ = self._run_check(self.QUIET, hour=hour, etag_match=False)
            assert r304.headers["X-Refresh-Interval"] == str(
                json.loads(r200.text)["refresh_interval"]
            ), f"paths disagree at {hour}:00"

    def test_multiplier_of_one_disables_quiet_hours(self):
        options = dict(self.QUIET, quiet_multiplier=1)
        resp, _ = self._run_check(options, hour=2, etag_match=True)
        assert resp.headers["X-Refresh-Interval"] == "15"

    def test_unset_quiet_hours_uses_base(self):
        resp, _ = self._run_check({"refresh_interval": 15}, hour=2, etag_match=True)
        assert resp.headers["X-Refresh-Interval"] == "15"

    def test_commanded_interval_is_recorded(self):
        """Unit 4's health detectors need to know what was actually commanded."""
        _, coordinator = self._run_check(self.QUIET, hour=2, etag_match=True)
        coordinator.record_commanded_interval.assert_called_once_with(120)

    def test_malformed_quiet_option_does_not_break_checkin(self):
        options = dict(self.QUIET, quiet_start="not a time")
        resp, _ = self._run_check(options, hour=2, etag_match=True)
        assert resp.status == 304
        assert resp.headers["X-Refresh-Interval"] == "15"

    def test_entity_base_overrides_stored_option(self):
        """The Number entity owns the live base, so automations take effect."""
        view, req, coordinator = self._setup(dict(self.QUIET), etag_match=True)
        coordinator.base_interval_minutes = 30
        import custom_components.eink_calendar.http_views as hv
        from unittest.mock import patch
        with patch.object(hv.dt_util, "now", return_value=self._at(12)):
            resp = _run(view.get(req, entry_id="entry-1", layer="check"))
        assert resp.headers["X-Refresh-Interval"] == "30"

    def test_falls_back_to_stored_option_when_entity_has_no_value(self):
        """Before the Number entity restores, the configured option still applies."""
        view, req, coordinator = self._setup(
            {"refresh_interval": 45}, etag_match=True
        )
        coordinator.base_interval_minutes = None
        import custom_components.eink_calendar.http_views as hv
        from unittest.mock import patch
        with patch.object(hv.dt_util, "now", return_value=self._at(12)):
            resp = _run(view.get(req, entry_id="entry-1", layer="check"))
        assert resp.headers["X-Refresh-Interval"] == "45"

    def test_junk_base_degrades_to_default(self):
        view, req, coordinator = self._setup({"refresh_interval": "???"}, etag_match=True)
        coordinator.base_interval_minutes = "also junk"
        import custom_components.eink_calendar.http_views as hv
        from unittest.mock import patch
        with patch.object(hv.dt_util, "now", return_value=self._at(12)):
            resp = _run(view.get(req, entry_id="entry-1", layer="check"))
        assert resp.headers["X-Refresh-Interval"] == "15"

    def test_announce_carries_the_baseline_not_quiet_hours(self):
        """Announce seeds the device's NVS fallback — it must stay stable.

        A quiet-hours value here would persist as the interval the device
        sleeps for whenever a check-in fails.
        """
        import custom_components.eink_calendar.http_views as hv
        from unittest.mock import patch

        entry = MagicMock()
        entry.options = dict(self.QUIET)
        coordinator = MagicMock()
        coordinator.base_interval_minutes = 15

        with patch.object(hv.dt_util, "now", return_value=self._at(2)):
            assert hv.base_interval(entry, coordinator) == 15
            assert hv.command_interval(entry, coordinator) == 120

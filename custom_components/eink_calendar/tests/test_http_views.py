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

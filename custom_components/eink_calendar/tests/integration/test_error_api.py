"""Integration tests for the /api/eink_calendar/error endpoint.

Tests the device error reporting API used by ESP32 to report issues.
"""

from __future__ import annotations

import aiohttp
import pytest

from .conftest import requires_ha, HA_TOKEN

pytestmark = [pytest.mark.asyncio, requires_ha]

requires_token = pytest.mark.skipif(
    not HA_TOKEN, reason="HA_TOKEN not set — cannot create config entries"
)


class TestErrorUnknownEntry:
    """Error reports for non-existent entries."""

    async def test_unknown_entry_returns_404(
        self, session: aiohttp.ClientSession, error_url: str
    ):
        """POST error to a non-existent entry_id should return 404."""
        url = error_url.format(entry_id="nonexistent_id")
        payload = {"error": "test_error", "details": "something broke"}
        async with session.post(url, json=payload) as resp:
            assert resp.status == 404


class TestErrorMacAuth:
    """MAC-based authentication on error endpoint."""

    async def test_error_with_bad_mac_placeholder(
        self, session: aiohttp.ClientSession, error_url: str
    ):
        """Smoke test: error endpoint returns 404 for unknown entry."""
        url = error_url.format(entry_id="fake_entry")
        headers = {"X-MAC": "00:00:00:00:00:00"}
        payload = {"error": "test_error"}
        async with session.post(url, json=payload, headers=headers) as resp:
            assert resp.status == 404


class TestErrorReporting:
    """Error reporting for configured devices."""

    @requires_token
    async def test_error_report_accepted(
        self,
        session: aiohttp.ClientSession,
        ha_url: str,
        ha_headers: dict[str, str],
        error_url: str,
    ):
        """POST error to a valid entry should return 200 with {status: ok}.

        Uses a manual entry (no MAC check) for simplicity.
        """
        # Create a manual config entry
        async with session.post(
            f"{ha_url}/api/config/config_entries/flow",
            headers=ha_headers,
            json={"handler": "eink_calendar"},
        ) as resp:
            if resp.status != 200:
                pytest.skip(f"Could not init config flow: HTTP {resp.status}")
            flow = await resp.json()

        async with session.post(
            f"{ha_url}/api/config/config_entries/flow/{flow['flow_id']}",
            headers=ha_headers,
            json={"device_name": "Error Test Device"},
        ) as resp:
            if resp.status != 200:
                pytest.skip(f"Could not complete flow: HTTP {resp.status}")
            result = await resp.json()

        if result.get("type") != "create_entry":
            pytest.skip(f"Flow did not create entry: {result}")

        entry_id = result["result"]["entry_id"]

        try:
            url = error_url.format(entry_id=entry_id)
            payload = {
                "error": "display_timeout",
                "details": "M1 busy timeout after 60s",
            }
            async with session.post(url, json=payload) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "ok"
        finally:
            # Cleanup
            async with session.delete(
                f"{ha_url}/api/config/config_entries/entry/{entry_id}",
                headers=ha_headers,
            ) as resp:
                pass

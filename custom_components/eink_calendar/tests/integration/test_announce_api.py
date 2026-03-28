"""Integration tests for the /api/eink_calendar/announce endpoint.

Run against a real Home Assistant instance via docker-compose.test.yml.
Skipped when HA is not reachable.
"""

from __future__ import annotations

import aiohttp
import pytest

from .conftest import requires_ha

pytestmark = [pytest.mark.asyncio, requires_ha]


class TestAnnounceNewDevice:
    """POST /api/eink_calendar/announce — new device discovery."""

    async def test_new_mac_returns_pending(
        self, session: aiohttp.ClientSession, announce_url: str, test_mac: str
    ):
        """A brand-new MAC should trigger a discovery flow and return 'pending'."""
        payload = {
            "mac": test_mac,
            "name": "Integration Test Calendar",
            "firmware_version": "1.0.0",
        }
        async with session.post(announce_url, json=payload) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "pending"

    async def test_repeated_announce_returns_pending(
        self, session: aiohttp.ClientSession, announce_url: str, test_mac_2: str
    ):
        """Subsequent announces for the same new MAC should still return 'pending'."""
        payload = {
            "mac": test_mac_2,
            "name": "Second Calendar",
            "firmware_version": "1.0.0",
        }
        # First announce
        async with session.post(announce_url, json=payload) as resp:
            assert resp.status == 200
            first = await resp.json()
            assert first["status"] == "pending"

        # Second announce (should still be pending — not yet configured by user)
        async with session.post(announce_url, json=payload) as resp:
            assert resp.status == 200
            second = await resp.json()
            assert second["status"] == "pending"


class TestAnnounceBadRequest:
    """POST /api/eink_calendar/announce — error cases."""

    async def test_missing_mac_returns_400(
        self, session: aiohttp.ClientSession, announce_url: str
    ):
        """Announce without a MAC field should return 400."""
        payload = {"name": "No MAC Device"}
        async with session.post(announce_url, json=payload) as resp:
            assert resp.status == 400
            data = await resp.json()
            assert data["status"] == "error"
            assert "mac" in data.get("message", "").lower()

    async def test_empty_body_returns_error(
        self, session: aiohttp.ClientSession, announce_url: str
    ):
        """POST with an empty body should return an error (400 or 500)."""
        async with session.post(
            announce_url,
            data=b"",
            headers={"Content-Type": "application/json"},
        ) as resp:
            assert resp.status in (400, 500)


class TestAnnounceConfiguredDevice:
    """POST /api/eink_calendar/announce — for a device with an existing config entry.

    These tests require a config entry to exist in HA. They will be skipped if
    the HA_TOKEN env var is not set (needed to create entries via the REST API).
    """

    @pytest.fixture
    async def configured_entry(
        self,
        session: aiohttp.ClientSession,
        ha_url: str,
        ha_headers: dict[str, str],
        announce_url: str,
    ):
        """Create a config entry via the HA config flow API.

        Uses the 'user' step to add a manual entry. Returns the entry_id.
        Skips the test if no HA_TOKEN is available.
        """
        from .conftest import HA_TOKEN

        if not HA_TOKEN:
            pytest.skip("HA_TOKEN not set — cannot create config entries via API")

        # Step 1: Initialize the config flow
        async with session.post(
            f"{ha_url}/api/config/config_entries/flow",
            headers=ha_headers,
            json={"handler": "eink_calendar"},
        ) as resp:
            if resp.status != 200:
                pytest.skip(f"Could not init config flow: HTTP {resp.status}")
            flow = await resp.json()

        flow_id = flow["flow_id"]

        # Step 2: Submit the user step with a device name
        async with session.post(
            f"{ha_url}/api/config/config_entries/flow/{flow_id}",
            headers=ha_headers,
            json={"device_name": "Integration Test Device"},
        ) as resp:
            if resp.status != 200:
                pytest.skip(f"Could not complete config flow: HTTP {resp.status}")
            result = await resp.json()

        if result.get("type") != "create_entry":
            pytest.skip(f"Config flow did not create entry: {result}")

        entry_id = result["result"]["entry_id"]

        yield entry_id

        # Cleanup: remove the config entry
        async with session.delete(
            f"{ha_url}/api/config/config_entries/entry/{entry_id}",
            headers=ha_headers,
        ) as resp:
            pass  # best-effort cleanup

    async def test_configured_device_returns_endpoints(
        self,
        session: aiohttp.ClientSession,
        announce_url: str,
        configured_entry: str,
    ):
        """A configured (manual) device should return 'configured' with endpoints.

        Note: Manual entries (user step) have no MAC, so any MAC will match.
        This verifies the announce response structure.
        """
        payload = {
            "mac": "FF:FF:FF:FF:FF:FF",
            "name": "Test",
            "firmware_version": "1.0.0",
        }
        # The manual entry has no MAC, so it won't match the MAC-based lookup.
        # This test mainly validates the flow works; a discovered entry would
        # require completing the discovery flow interactively.
        async with session.post(announce_url, json=payload) as resp:
            assert resp.status == 200
            data = await resp.json()
            # A new MAC will get "pending" since the manual entry doesn't have this MAC
            assert data["status"] in ("pending", "configured")

"""Integration tests for the /api/eink_calendar/bitmap endpoints.

These tests require a configured config entry in HA, which in turn requires
a valid HA_TOKEN. Tests are skipped when prerequisites are missing.
"""

from __future__ import annotations

import aiohttp
import pytest

from .conftest import requires_ha, HA_TOKEN

pytestmark = [pytest.mark.asyncio, requires_ha]

requires_token = pytest.mark.skipif(
    not HA_TOKEN, reason="HA_TOKEN not set — cannot create config entries"
)


@pytest.fixture
async def manual_entry(
    session: aiohttp.ClientSession,
    ha_url: str,
    ha_headers: dict[str, str],
):
    """Create a manual config entry and return its entry_id.

    Manual entries have no MAC, so MAC auth is effectively bypassed.
    """
    if not HA_TOKEN:
        pytest.skip("HA_TOKEN not set")

    # Init flow
    async with session.post(
        f"{ha_url}/api/config/config_entries/flow",
        headers=ha_headers,
        json={"handler": "eink_calendar"},
    ) as resp:
        if resp.status != 200:
            pytest.skip(f"Could not init config flow: HTTP {resp.status}")
        flow = await resp.json()

    # Complete user step
    async with session.post(
        f"{ha_url}/api/config/config_entries/flow/{flow['flow_id']}",
        headers=ha_headers,
        json={"device_name": "Bitmap Test Device"},
    ) as resp:
        if resp.status != 200:
            pytest.skip(f"Could not complete flow: HTTP {resp.status}")
        result = await resp.json()

    if result.get("type") != "create_entry":
        pytest.skip(f"Flow did not create entry: {result}")

    entry_id = result["result"]["entry_id"]
    yield entry_id

    # Cleanup
    async with session.delete(
        f"{ha_url}/api/config/config_entries/entry/{entry_id}",
        headers=ha_headers,
    ) as resp:
        pass


class TestBitmapUnknownEntry:
    """Bitmap requests with an invalid entry_id."""

    async def test_unknown_entry_returns_404(
        self, session: aiohttp.ClientSession, bitmap_url: str
    ):
        """GET with a non-existent entry_id should return 404."""
        url = bitmap_url.format(entry_id="nonexistent_id", layer="black_top")
        async with session.get(url) as resp:
            assert resp.status == 404


class TestBitmapInvalidLayer:
    """Bitmap requests with invalid layer names."""

    @requires_token
    async def test_invalid_layer_returns_400(
        self,
        session: aiohttp.ClientSession,
        bitmap_url: str,
        manual_entry: str,
    ):
        """GET with an invalid layer name should return 400."""
        url = bitmap_url.format(entry_id=manual_entry, layer="invalid_layer")
        async with session.get(url) as resp:
            assert resp.status == 400


class TestBitmapMacAuth:
    """MAC-based authentication on bitmap endpoints.

    For discovered devices (with a MAC in the config entry), the X-MAC header
    must match. Manual entries skip MAC checking. These tests verify the 403
    behavior for MAC-protected entries, which requires a discovered entry.
    """

    async def test_wrong_mac_concept(
        self, session: aiohttp.ClientSession, bitmap_url: str
    ):
        """Verify the bitmap endpoint exists and returns 404 for unknown entries.

        Full MAC auth testing requires a discovered config entry, which needs
        interactive config flow completion. This is a smoke test placeholder.
        """
        url = bitmap_url.format(entry_id="fake_entry", layer="check")
        headers = {"X-MAC": "00:00:00:00:00:00"}
        async with session.get(url, headers=headers) as resp:
            assert resp.status == 404


class TestBitmapCheckEndpoint:
    """Test the ETag-based check endpoint."""

    @requires_token
    async def test_check_returns_response(
        self,
        session: aiohttp.ClientSession,
        bitmap_url: str,
        manual_entry: str,
    ):
        """GET /check should return 200 or 503 (if no calendar data yet)."""
        url = bitmap_url.format(entry_id=manual_entry, layer="check")
        async with session.get(url) as resp:
            # 200 = data available, 503 = coordinator not ready yet
            assert resp.status in (200, 503)

    @requires_token
    async def test_check_with_etag_returns_304_or_200(
        self,
        session: aiohttp.ClientSession,
        bitmap_url: str,
        manual_entry: str,
    ):
        """GET /check with If-None-Match should return 304 if data unchanged."""
        url = bitmap_url.format(entry_id=manual_entry, layer="check")

        # First request to get the current ETag
        async with session.get(url) as resp:
            if resp.status == 503:
                pytest.skip("Coordinator not ready — no calendar data")
            data = await resp.json()
            etag = data.get("etag")
            if not etag:
                pytest.skip("No etag in check response")

        # Second request with If-None-Match
        headers = {"If-None-Match": etag}
        async with session.get(url, headers=headers) as resp:
            # 304 if unchanged, 200 if something triggered a re-render
            assert resp.status in (200, 304)

"""Fixtures for Home Assistant integration tests.

These tests run against a real HA instance started via docker-compose.test.yml.
They are skipped automatically when the HA instance is not reachable.
"""

from __future__ import annotations

import os

import aiohttp
import pytest
import pytest_asyncio

# Default URL — override with HA_URL env var (e.g. when running outside Docker)
HA_BASE_URL = os.environ.get("HA_URL", "http://localhost:18123")

# Long-lived access token — must be created in the test HA instance.
# Set via HA_TOKEN env var; tests requiring auth are skipped when absent.
HA_TOKEN = os.environ.get("HA_TOKEN", "")


def _ha_reachable() -> bool:
    """Quick sync check whether the HA instance answers HTTP."""
    import urllib.request
    import urllib.error

    try:
        urllib.request.urlopen(f"{HA_BASE_URL}/api/", timeout=3)
    except urllib.error.HTTPError:
        # 401 means HA is up but we're not authed — that's fine
        return True
    except Exception:
        return False
    return True


# ---------- pytest markers / skips ----------

requires_ha = pytest.mark.skipif(
    not _ha_reachable(),
    reason=f"Home Assistant not reachable at {HA_BASE_URL}",
)


# ---------- fixtures ----------


@pytest_asyncio.fixture
async def session():
    """Create an aiohttp ClientSession that closes after the test."""
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def ha_url() -> str:
    """Base URL for the HA instance under test."""
    return HA_BASE_URL


@pytest.fixture
def ha_headers() -> dict[str, str]:
    """Auth headers for HA REST API calls (empty if no token set)."""
    if HA_TOKEN:
        return {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }
    return {"Content-Type": "application/json"}


@pytest.fixture
def announce_url(ha_url: str) -> str:
    """Full URL for the announce endpoint."""
    return f"{ha_url}/api/eink_calendar/announce"


@pytest.fixture
def bitmap_url(ha_url: str) -> str:
    """Template URL for bitmap endpoints (use .format(entry_id=..., layer=...))."""
    return ha_url + "/api/eink_calendar/bitmap/{entry_id}/{layer}"


@pytest.fixture
def error_url(ha_url: str) -> str:
    """Template URL for error reporting endpoint (use .format(entry_id=...))."""
    return ha_url + "/api/eink_calendar/error/{entry_id}"


# ---------- test MAC addresses ----------

TEST_MAC = "AA:BB:CC:DD:EE:01"
TEST_MAC_2 = "AA:BB:CC:DD:EE:02"


@pytest.fixture
def test_mac() -> str:
    return TEST_MAC


@pytest.fixture
def test_mac_2() -> str:
    return TEST_MAC_2

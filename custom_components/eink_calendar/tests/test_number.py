"""Tests for the refresh-interval Number entity.

conftest mocks Home Assistant wholesale, so — as in test_http_views — real
enough base classes are installed before importing the module under test.
"""

import asyncio
import sys
from unittest.mock import MagicMock


class _FakeNumberEntity:
    """Minimal stand-in for NumberEntity."""

    _attr_native_value = None

    def async_write_ha_state(self):
        self._state_written = True


class _FakeRestoreNumber(_FakeNumberEntity):
    """Stand-in for RestoreNumber with a settable restore payload."""

    _restored = None

    async def async_get_last_number_data(self):
        return self._restored

    async def async_added_to_hass(self):
        return None


sys.modules.setdefault("homeassistant.components.number", MagicMock())
sys.modules.setdefault("homeassistant.helpers.restore_state", MagicMock())
sys.modules["homeassistant.components.number"].NumberEntity = _FakeNumberEntity
sys.modules["homeassistant.components.number"].RestoreNumber = _FakeRestoreNumber

_key = "custom_components.eink_calendar.number"
if _key in sys.modules:
    del sys.modules[_key]

from custom_components.eink_calendar.number import (  # noqa: E402
    EinkCalendarRefreshIntervalNumber,
)


def _run(coro):
    """Run an async coroutine on a fresh loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_entry(refresh_interval=15):
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {"mac_address": "AA:BB:CC:DD:EE:FF", "device_name": "Kitchen"}
    entry.options = {"refresh_interval": refresh_interval}
    return entry


def make_number(refresh_interval=15):
    entry = make_entry(refresh_interval)
    coordinator = MagicMock()
    coordinator.base_interval_minutes = refresh_interval
    return EinkCalendarRefreshIntervalNumber(coordinator, entry), coordinator


class TestSeeding:
    def test_reports_coordinator_base(self):
        number, _ = make_number(refresh_interval=20)
        assert number.native_value == 20

    def test_unique_id_is_entry_scoped(self):
        number, _ = make_number()
        assert number.unique_id == "entry-1_refresh_interval"

    def test_bounds_are_legal_wire_values(self):
        """Must match the protocol: integer minutes, 1..1440."""
        number, _ = make_number()
        assert number.native_min_value == 1
        assert number.native_max_value == 1440
        assert number.native_step == 1


class TestSetValue:
    def test_set_updates_the_coordinator_base(self):
        number, coordinator = make_number()
        _run(number.async_set_native_value(45))
        assert coordinator.base_interval_minutes == 45

    def test_set_is_reflected_in_native_value(self):
        number, _ = make_number()
        _run(number.async_set_native_value(45))
        assert number.native_value == 45

    def test_set_stores_whole_minutes(self):
        """HA hands back floats; the wire format is integer minutes."""
        number, coordinator = make_number()
        _run(number.async_set_native_value(30.0))
        assert coordinator.base_interval_minutes == 30
        assert isinstance(coordinator.base_interval_minutes, int)


class TestRestore:
    def test_restores_previous_value_on_startup(self):
        number, coordinator = make_number(refresh_interval=15)
        restored = MagicMock()
        restored.native_value = 60
        number._restored = restored
        _run(number.async_added_to_hass())
        assert coordinator.base_interval_minutes == 60

    def test_without_restore_data_keeps_the_option_value(self):
        number, coordinator = make_number(refresh_interval=15)
        number._restored = None
        _run(number.async_added_to_hass())
        assert coordinator.base_interval_minutes == 15

    def test_ignores_out_of_range_restore(self):
        """A corrupt restored value must not command an illegal interval."""
        number, coordinator = make_number(refresh_interval=15)
        restored = MagicMock()
        restored.native_value = 99999
        number._restored = restored
        _run(number.async_added_to_hass())
        assert coordinator.base_interval_minutes == 15

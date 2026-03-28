"""Tests for UpdateFailed exception handling in coordinator._async_update_data()."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.eink_calendar.const import (
    CONF_CALENDARS,
    CONF_DEVICE_NAME,
    CONF_MAC_ADDRESS,
    DOMAIN,
)
from custom_components.eink_calendar.coordinator import EinkCalendarDataCoordinator


def make_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    return hass


def make_entry(calendars=None):
    entry = MagicMock()
    entry.entry_id = "test-entry-1"
    entry.data = {CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:FF", CONF_DEVICE_NAME: "Test"}
    entry.options = {CONF_CALENDARS: calendars or ["calendar.test"]}
    return entry


def make_coordinator(hass=None, entry=None):
    hass = hass or make_hass()
    entry = entry or make_entry()
    return EinkCalendarDataCoordinator(hass, entry)


class TestUpdateFailedPropagation:
    """UpdateFailed raised internally should propagate without double-wrapping."""

    def test_update_failed_propagates_unchanged(self):
        """When _fetch_calendar_events raises UpdateFailed, it should propagate as-is."""
        coord = make_coordinator()
        original_error = UpdateFailed("Calendar entities not ready yet")

        with patch.object(
            coord, "_fetch_calendar_events", new_callable=AsyncMock, side_effect=original_error
        ), patch.object(
            coord, "_fetch_waste_calendar_events", new_callable=AsyncMock, return_value=[]
        ), patch.object(
            coord, "_fetch_weather_data", new_callable=AsyncMock, return_value=None
        ):
            try:
                asyncio.run(coord._async_update_data())
                assert False, "Expected UpdateFailed to be raised"
            except UpdateFailed as exc:
                # The exception should be the exact same object, not wrapped
                assert exc is original_error
                # The message should NOT contain the "Error communicating" wrapper
                assert "Error communicating with API" not in str(exc)
                assert "Calendar entities not ready yet" in str(exc)

    def test_generic_exception_gets_wrapped_in_update_failed(self):
        """When _fetch_calendar_events raises a generic Exception, it gets wrapped."""
        coord = make_coordinator()
        original_error = RuntimeError("Connection timed out")

        with patch.object(
            coord, "_fetch_calendar_events", new_callable=AsyncMock, side_effect=original_error
        ), patch.object(
            coord, "_fetch_waste_calendar_events", new_callable=AsyncMock, return_value=[]
        ), patch.object(
            coord, "_fetch_weather_data", new_callable=AsyncMock, return_value=None
        ):
            try:
                asyncio.run(coord._async_update_data())
                assert False, "Expected UpdateFailed to be raised"
            except UpdateFailed as exc:
                assert "Error communicating with API" in str(exc)
                assert "Connection timed out" in str(exc)
                assert exc.__cause__ is original_error

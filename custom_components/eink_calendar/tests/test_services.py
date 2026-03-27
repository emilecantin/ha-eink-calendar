"""Tests for E-Ink Calendar services."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.eink_calendar.services import (
    SERVICE_TRIGGER_RENDER,
    async_setup_services,
    async_unload_services,
)
from custom_components.eink_calendar.const import DOMAIN


# ---- Helpers ----


def make_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.services = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()
    hass.config_entries = MagicMock()
    return hass


def make_entry(entry_id):
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def make_coordinator():
    coord = MagicMock()
    coord.invalidate_render_cache = MagicMock()
    coord.async_refresh = AsyncMock()
    return coord


# ---- Tests: trigger_render ----


def get_trigger_render_handler(hass):
    """Extract the trigger_render handler from registered service calls."""
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == SERVICE_TRIGGER_RENDER:
            return call[0][2]
    raise AssertionError("trigger_render service not registered")


class TestTriggerRender:
    def test_refreshes_all_coordinators(self):
        """trigger_render must refresh ALL coordinators, not just one."""
        hass = make_hass()
        coord_a = make_coordinator()
        coord_b = make_coordinator()

        hass.data[DOMAIN] = {
            "entry_a_id": coord_a,
            "entry_b_id": coord_b,
            "http_views_registered": True,  # non-coordinator, should be skipped
        }

        # Register the service
        asyncio.run(async_setup_services(hass))

        # Get the registered handler
        handler = get_trigger_render_handler(hass)

        # Call it
        asyncio.run(handler(MagicMock()))

        coord_a.invalidate_render_cache.assert_called_once()
        coord_a.async_refresh.assert_awaited_once()
        coord_b.invalidate_render_cache.assert_called_once()
        coord_b.async_refresh.assert_awaited_once()

    def test_skips_non_coordinator_entries(self):
        """Non-coordinator entries (like 'http_views_registered') must be skipped."""
        hass = make_hass()
        hass.data[DOMAIN] = {"http_views_registered": True}

        asyncio.run(async_setup_services(hass))
        handler = get_trigger_render_handler(hass)

        # Should not raise
        asyncio.run(handler(MagicMock()))


# ---- Tests: unload services ----


class TestUnloadServices:
    def test_keeps_service_when_other_entries_exist(self):
        """Unloading one entry must NOT remove service when another exists."""
        hass = make_hass()
        hass.services.has_service.return_value = True

        entry_a = make_entry("entry_a_id")
        entry_b = make_entry("entry_b_id")
        hass.config_entries.async_entries = MagicMock(
            return_value=[entry_a, entry_b]
        )

        asyncio.run(async_unload_services(hass, entry_a))

        hass.services.async_remove.assert_not_called()

    def test_removes_service_when_last_entry(self):
        """Unloading the last entry MUST remove the services."""
        hass = make_hass()
        hass.services.has_service.return_value = True

        entry_a = make_entry("entry_a_id")
        hass.config_entries.async_entries = MagicMock(return_value=[entry_a])

        asyncio.run(async_unload_services(hass, entry_a))

        # Both services should be removed
        remove_calls = hass.services.async_remove.call_args_list
        removed_services = {call[0][1] for call in remove_calls}
        assert SERVICE_TRIGGER_RENDER in removed_services

    def test_noop_when_service_not_registered(self):
        """Unload should be a no-op if the service isn't registered."""
        hass = make_hass()
        hass.services.has_service.return_value = False

        entry_a = make_entry("entry_a_id")

        asyncio.run(async_unload_services(hass, entry_a))

        hass.services.async_remove.assert_not_called()

    def test_service_registered_only_once(self):
        """Each service is registered only once even with multiple setup calls."""
        hass = make_hass()
        hass.services.has_service.return_value = False
        asyncio.run(async_setup_services(hass))
        first_call_count = hass.services.async_register.call_count

        hass.services.has_service.return_value = True
        asyncio.run(async_setup_services(hass))

        # No additional registrations on second call
        assert hass.services.async_register.call_count == first_call_count

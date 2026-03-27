"""Services for E-Ink Calendar."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_TRIGGER_RENDER = "trigger_render"

TRIGGER_RENDER_SCHEMA = vol.Schema({})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for E-Ink Calendar."""

    async def handle_trigger_render(call: ServiceCall) -> None:
        """Trigger a manual re-render for all configured calendars."""
        domain_data = hass.data.get(DOMAIN, {})
        refreshed = 0
        for key, coordinator in domain_data.items():
            if not hasattr(coordinator, "force_refresh"):
                continue
            coordinator.force_refresh()
            await coordinator.async_refresh()
            refreshed += 1

        _LOGGER.info("Manual render triggered for %d entries", refreshed)

    # Only register if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_TRIGGER_RENDER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TRIGGER_RENDER,
            handle_trigger_render,
            schema=TRIGGER_RENDER_SCHEMA,
        )

    _LOGGER.info("E-Ink Calendar services registered")


async def async_unload_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unload E-Ink Calendar services (only when last entry is removed)."""
    if not hass.services.has_service(DOMAIN, SERVICE_TRIGGER_RENDER):
        return

    remaining = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not remaining:
        hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_RENDER)

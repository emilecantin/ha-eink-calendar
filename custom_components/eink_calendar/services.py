"""Services for E-Ink Calendar."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_TRIGGER_RENDER = "trigger_render"

TRIGGER_RENDER_SCHEMA = vol.Schema({})


async def async_setup_services(hass: HomeAssistant, entry) -> None:
    """Set up services for E-Ink Calendar."""

    async def handle_trigger_render(call: ServiceCall) -> None:
        """Trigger a manual re-render of the calendar."""
        coordinator = hass.data[DOMAIN].get(entry.entry_id)
        if not coordinator:
            _LOGGER.error("Coordinator not found for entry %s", entry.entry_id)
            return

        coordinator.invalidate_render_cache()
        await coordinator.async_refresh()

        _LOGGER.info("Manual render triggered for entry %s", entry.entry_id)

    # Only register if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_TRIGGER_RENDER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TRIGGER_RENDER,
            handle_trigger_render,
            schema=TRIGGER_RENDER_SCHEMA,
        )

    _LOGGER.info("E-Ink Calendar services registered")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload E-Ink Calendar services."""
    if hass.services.has_service(DOMAIN, SERVICE_TRIGGER_RENDER):
        hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_RENDER)

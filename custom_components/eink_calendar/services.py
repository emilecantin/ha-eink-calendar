"""Services for E-Ink Calendar."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, FIRMWARE_MANAGER_KEY, SERVICE_UPLOAD_FIRMWARE

_LOGGER = logging.getLogger(__name__)

SERVICE_TRIGGER_RENDER = "trigger_render"

TRIGGER_RENDER_SCHEMA = vol.Schema({})

UPLOAD_FIRMWARE_SCHEMA = vol.Schema(
    {
        vol.Required("file_path"): str,
        vol.Required("version"): str,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for E-Ink Calendar."""

    async def handle_trigger_render(call: ServiceCall) -> None:
        """Trigger a manual re-render for all configured calendars."""
        domain_data = hass.data.get(DOMAIN, {})
        refreshed = 0
        for key, coordinator in domain_data.items():
            if not hasattr(coordinator, "invalidate_render_cache"):
                continue
            coordinator.invalidate_render_cache()
            await coordinator.async_refresh()
            refreshed += 1

        _LOGGER.info("Manual render triggered for %d entries", refreshed)

    async def handle_upload_firmware(call: ServiceCall) -> None:
        """Upload a firmware binary for OTA updates."""
        import os

        file_path = call.data["file_path"]
        version = call.data["version"]

        if not await hass.async_add_executor_job(os.path.isfile, file_path):
            _LOGGER.error("Firmware file not found: %s", file_path)
            return

        if not file_path.endswith(".bin"):
            _LOGGER.error("Firmware file must be a .bin file: %s", file_path)
            return

        fw_manager = hass.data[DOMAIN].get(FIRMWARE_MANAGER_KEY)
        if not fw_manager:
            _LOGGER.error("Firmware manager not initialized")
            return

        await hass.async_add_executor_job(
            fw_manager.store_firmware_from_file, file_path, version
        )

        _LOGGER.info("Firmware v%s uploaded from %s", version, file_path)

    # Only register if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_TRIGGER_RENDER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TRIGGER_RENDER,
            handle_trigger_render,
            schema=TRIGGER_RENDER_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_UPLOAD_FIRMWARE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPLOAD_FIRMWARE,
            handle_upload_firmware,
            schema=UPLOAD_FIRMWARE_SCHEMA,
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
    if hass.services.has_service(DOMAIN, SERVICE_UPLOAD_FIRMWARE):
        hass.services.async_remove(DOMAIN, SERVICE_UPLOAD_FIRMWARE)

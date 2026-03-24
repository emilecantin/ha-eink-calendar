"""The E-Ink Calendar integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_CALENDARS,
    CONF_DEVICE_NAME,
    CONF_MAC_ADDRESS,
    CONF_WASTE_CALENDARS,
    DOMAIN,
)
from .coordinator import EinkCalendarDataCoordinator
from .http_views import setup_http_views
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.IMAGE, Platform.SENSOR]


def ensure_http_views(hass: HomeAssistant) -> None:
    """Register HTTP views if not already done."""
    hass.data.setdefault(DOMAIN, {})
    if "http_views_registered" not in hass.data[DOMAIN]:
        setup_http_views(hass)
        hass.data[DOMAIN]["http_views_registered"] = True
        _LOGGER.debug("HTTP views registered")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the E-Ink Calendar integration (called before config entries)."""
    # Register HTTP views early so the announce endpoint is available
    # before any device is configured
    ensure_http_views(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up E-Ink Calendar from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Wait for calendar entities to be ready (race condition fix)
    calendar_ids = entry.options.get(CONF_CALENDARS, [])
    waste_calendar_ids = entry.options.get(CONF_WASTE_CALENDARS, [])
    all_calendar_ids = calendar_ids + waste_calendar_ids

    if all_calendar_ids:
        _LOGGER.debug("Waiting for calendar entities to be ready: %s", all_calendar_ids)
        for i in range(30):
            all_found = all(hass.states.get(cal_id) for cal_id in all_calendar_ids)
            if all_found:
                _LOGGER.debug("All calendar entities ready after %d seconds", i)
                break
            if i == 29:
                _LOGGER.warning(
                    "Some calendar entities not ready after 30 seconds: %s",
                    [
                        cal_id
                        for cal_id in all_calendar_ids
                        if not hass.states.get(cal_id)
                    ],
                )
            await asyncio.sleep(1)

    # Create data coordinator
    coordinator = EinkCalendarDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Ensure HTTP views are registered (fallback if async_setup wasn't called)
    ensure_http_views(hass)

    # Register services
    await async_setup_services(hass, entry)

    # Register device - use MAC as identifier if available, otherwise entry_id
    mac = entry.data.get(CONF_MAC_ADDRESS)
    identifiers = {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)}

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=identifiers,
        name=entry.data.get(CONF_DEVICE_NAME, "E-Ink Calendar"),
        manufacturer="E-Ink Calendar",
        model="ESP32 E-Paper Display",
        sw_version=entry.data.get("firmware_version", "0.1.0"),
    )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await async_unload_services(hass)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)

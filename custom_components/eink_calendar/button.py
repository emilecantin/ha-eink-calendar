"""Button entities for E-Paper Calendar."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_NAME, CONF_MAC_ADDRESS, DOMAIN
from .coordinator import EinkCalendarDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E-Paper Calendar buttons from a config entry."""
    coordinator: EinkCalendarDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            EinkCalendarForceRefreshButton(coordinator, entry),
        ]
    )


class EinkCalendarForceRefreshButton(ButtonEntity):
    """Button to force the ESP32 to re-download bitmaps on next check-in."""

    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Force Refresh"
        self._attr_unique_id = f"{entry.entry_id}_force_refresh"
        mac = entry.data.get(CONF_MAC_ADDRESS)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)},
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        self.coordinator.force_refresh()
        await self.coordinator.async_refresh()
        _LOGGER.info("Force refresh queued for next ESP32 check-in")

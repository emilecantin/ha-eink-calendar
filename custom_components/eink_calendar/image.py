"""Image entities for E-Paper Calendar bitmap layers."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_NAME,
    CONF_MAC_ADDRESS,
    DOMAIN,
    IMAGE_BLACK_BOTTOM_NAME,
    IMAGE_BLACK_TOP_NAME,
    IMAGE_RED_BOTTOM_NAME,
    IMAGE_RED_TOP_NAME,
)
from .coordinator import EinkCalendarDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E-Paper Calendar image entities from a config entry."""
    coordinator: EinkCalendarDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            EinkCalendarBitmapImage(coordinator, entry, "black_top", IMAGE_BLACK_TOP_NAME),
            EinkCalendarBitmapImage(
                coordinator, entry, "black_bottom", IMAGE_BLACK_BOTTOM_NAME
            ),
            EinkCalendarBitmapImage(coordinator, entry, "red_top", IMAGE_RED_TOP_NAME),
            EinkCalendarBitmapImage(coordinator, entry, "red_bottom", IMAGE_RED_BOTTOM_NAME),
        ]
    )


class EinkCalendarBitmapImage(ImageEntity):
    """Image entity serving bitmap layers for ESP32."""

    def __init__(
        self,
        coordinator: EinkCalendarDataCoordinator,
        entry: ConfigEntry,
        layer_type: str,
        entity_name: str,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(coordinator.hass)
        self.coordinator = coordinator
        self.entry = entry
        self.layer_type = layer_type
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} {entity_name.replace('_', ' ').title()}"
        self._attr_unique_id = f"{entry.entry_id}_{entity_name}"
        mac = entry.data.get(CONF_MAC_ADDRESS)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)},
        }
        self._attr_content_type = "application/octet-stream"
        self._render_timestamp: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        # Trigger initial render
        await self._update_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.hass.async_create_task(self._update_from_coordinator())

    async def _update_from_coordinator(self) -> None:
        """Fetch rendered data and update image timestamp."""
        rendered = await self.coordinator.async_get_rendered()
        if rendered and rendered.timestamp != self._render_timestamp:
            self._render_timestamp = rendered.timestamp
            self._attr_image_last_updated = rendered.timestamp
            self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Return image bytes."""
        rendered = await self.coordinator.async_get_rendered()
        if not rendered:
            return None

        if self.layer_type == "black_top":
            return rendered.get_black_top()
        elif self.layer_type == "black_bottom":
            return rendered.get_black_bottom()
        elif self.layer_type == "red_top":
            return rendered.get_red_top()
        elif self.layer_type == "red_bottom":
            return rendered.get_red_bottom()

        return None

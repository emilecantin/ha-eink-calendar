"""Camera entity for E-Paper Calendar preview."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CAMERA_NAME, CONF_DEVICE_NAME, CONF_MAC_ADDRESS, DOMAIN
from .coordinator import EinkCalendarDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E-Paper Calendar camera from a config entry."""
    coordinator: EinkCalendarDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([EinkCalendarPreviewCamera(coordinator, entry)])


class EinkCalendarPreviewCamera(Camera):
    """Camera entity showing calendar preview."""

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the camera."""
        super().__init__()
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = (
            f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} {CAMERA_NAME.title()}"
        )
        self._attr_unique_id = f"{entry.entry_id}_{CAMERA_NAME}"
        mac = entry.data.get(CONF_MAC_ADDRESS)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)},
        }
        self._cached_image: bytes | None = None
        self._cached_data_timestamp: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener to invalidate cache on data change."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Invalidate cached image when coordinator data changes."""
        data = self.coordinator.data
        new_ts = data.get("timestamp") if data else None
        if new_ts != self._cached_data_timestamp:
            self._cached_image = None
            self.async_write_ha_state()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return calendar preview image (cached until data changes)."""
        if self._cached_image is not None:
            return self._cached_image

        try:
            rendered = await self.coordinator.async_get_rendered()
            if rendered is None:
                _LOGGER.warning("No data available for camera")
                return None

            self._cached_image = rendered.preview_png
            self._cached_data_timestamp = rendered.timestamp

            return rendered.preview_png
        except Exception as err:
            _LOGGER.error("Error rendering camera image: %s", err, exc_info=True)
            return None

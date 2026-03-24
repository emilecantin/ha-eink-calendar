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
from .renderer.renderer import render_to_png

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
        self._last_render_time: datetime | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return calendar preview image."""
        try:
            data = self.coordinator.data
            if not data:
                _LOGGER.warning("No data available for camera")
                return self._cached_image

            # Render to PNG
            png_data = await self.hass.async_add_executor_job(
                render_to_png,
                data.get("calendar_events", []),
                data.get("waste_events", []),
                data.get("weather_data"),
                data.get("timestamp", datetime.now()),
                self.entry.options,
            )

            self._cached_image = png_data
            self._last_render_time = datetime.now()

            return png_data
        except Exception as err:
            _LOGGER.error("Error rendering camera image: %s", err, exc_info=True)
            return self._cached_image

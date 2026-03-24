"""Image entities for E-Paper Calendar bitmap layers."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
from .renderer.renderer import RenderedCalendar, render_calendar

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
        self._cached_render: RenderedCalendar | None = None
        self._last_render_time: datetime | None = None
        self._last_config_hash: int | None = None

    def _needs_render(self) -> bool:
        """Check if re-render is needed."""
        if self._cached_render is None:
            return True

        # Check if manual render was triggered
        if self.coordinator.data and self.coordinator.data.get("force_render"):
            _LOGGER.debug("Manual render triggered, re-rendering")
            return True

        # Check if configuration changed (convert lists to tuples for hashing)
        config_items = []
        for k, v in self.entry.options.items():
            if isinstance(v, list):
                config_items.append((k, tuple(v)))
            else:
                config_items.append((k, v))
        config_hash = hash(frozenset(config_items))
        if config_hash != self._last_config_hash:
            _LOGGER.debug("Configuration changed, re-rendering")
            self._last_config_hash = config_hash
            return True

        # Check if coordinator data changed
        if (
            self.coordinator.data
            and self.coordinator.data.get("timestamp") != self._cached_render.timestamp
        ):
            _LOGGER.debug("Coordinator data changed, re-rendering")
            return True

        return False

    async def async_image(self) -> bytes | None:
        """Return image bytes."""
        try:
            # Re-render if needed
            if self._needs_render():
                data = self.coordinator.data
                if not data:
                    _LOGGER.warning("No coordinator data available")
                    return self._get_cached_chunk()

                # Render calendar
                rendered = await self.hass.async_add_executor_job(
                    render_calendar,
                    data.get("calendar_events", []),
                    data.get("waste_events", []),
                    data.get("weather_data"),
                    data.get("timestamp", datetime.now()),
                    self.entry.options,
                )

                self._cached_render = rendered
                self._last_render_time = datetime.now()
                # Convert lists to tuples for hashing
                config_items = []
                for k, v in self.entry.options.items():
                    if isinstance(v, list):
                        config_items.append((k, tuple(v)))
                    else:
                        config_items.append((k, v))
                self._last_config_hash = hash(frozenset(config_items))

                _LOGGER.debug("Rendered new calendar (ETag: %s)", rendered.etag[:8])

            return self._get_cached_chunk()

        except Exception as err:
            _LOGGER.error(
                "Error rendering image for %s: %s", self.layer_type, err, exc_info=True
            )
            return self._get_cached_chunk()

    def _get_cached_chunk(self) -> bytes | None:
        """Get the appropriate chunk from cached render."""
        if not self._cached_render:
            return None

        if self.layer_type == "black_top":
            return self._cached_render.get_black_top()
        elif self.layer_type == "black_bottom":
            return self._cached_render.get_black_bottom()
        elif self.layer_type == "red_top":
            return self._cached_render.get_red_top()
        elif self.layer_type == "red_bottom":
            return self._cached_render.get_red_bottom()

        return None

    @property
    def image_last_updated(self) -> datetime | None:
        """Return timestamp of last render."""
        return self._last_render_time

"""Sensor entities for E-Paper Calendar."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_NAME, DOMAIN, SENSOR_LAST_UPDATE_NAME
from .coordinator import EpcalDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E-Paper Calendar sensors from a config entry."""
    coordinator: EpcalDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            EpcalLastUpdateSensor(coordinator, entry),
        ]
    )


class EpcalLastUpdateSensor(SensorEntity):
    """Sensor showing last render timestamp."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: EpcalDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'EPCAL')} {SENSOR_LAST_UPDATE_NAME.replace('_', ' ').title()}"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_UPDATE_NAME}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp."""
        if self.coordinator.data:
            return self.coordinator.data.get("timestamp")
        return None

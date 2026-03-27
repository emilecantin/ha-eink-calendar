"""Sensor entities for E-Paper Calendar."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_NAME, CONF_MAC_ADDRESS, DOMAIN, SENSOR_FIRMWARE_VERSION_NAME, SENSOR_LAST_CHECKIN_NAME, SENSOR_LAST_UPDATE_NAME
from .coordinator import EinkCalendarDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E-Paper Calendar sensors from a config entry."""
    coordinator: EinkCalendarDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            EinkCalendarLastUpdateSensor(coordinator, entry),
            EinkCalendarLastCheckinSensor(coordinator, entry),
            EinkCalendarFirmwareVersionSensor(coordinator, entry),
        ]
    )


class EinkCalendarLastUpdateSensor(SensorEntity):
    """Sensor showing when the display image last changed."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} {SENSOR_LAST_UPDATE_NAME.replace('_', ' ').title()}"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_UPDATE_NAME}"
        mac = entry.data.get(CONF_MAC_ADDRESS)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)},
        }
        self._last_written_value: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Register listener when entity is added."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        current = self.coordinator.last_image_change
        if current != self._last_written_value:
            self._last_written_value = current
            self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the last image change."""
        return self.coordinator.last_image_change


class EinkCalendarLastCheckinSensor(SensorEntity):
    """Sensor showing last time the ESP32 checked in."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:access-point-check"

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Last Check-in"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_CHECKIN_NAME}"
        mac = entry.data.get(CONF_MAC_ADDRESS)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)},
        }
        self._last_written_value: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Register listener when entity is added."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        current = self.coordinator.last_checkin
        if current != self._last_written_value:
            self._last_written_value = current
            self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        """Return the last check-in timestamp."""
        return self.coordinator.last_checkin


class EinkCalendarFirmwareVersionSensor(SensorEntity):
    """Sensor showing the ESP32's firmware version."""

    _attr_icon = "mdi:chip"

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Firmware Version"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_FIRMWARE_VERSION_NAME}"
        mac = entry.data.get(CONF_MAC_ADDRESS)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)},
        }
        self._last_written_value: str | None = None

    async def async_added_to_hass(self) -> None:
        """Register listener when entity is added."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        current = self.coordinator.firmware_version
        if current != self._last_written_value:
            self._last_written_value = current
            self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return the firmware version string."""
        return self.coordinator.firmware_version

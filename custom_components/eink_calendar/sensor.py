"""Sensor entities for E-Paper Calendar."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_NAME, CONF_MAC_ADDRESS, DOMAIN, SENSOR_CHECKIN_COUNT_NAME, SENSOR_DEVICE_ETAG_NAME, SENSOR_DEVICE_STATUS_NAME, SENSOR_FIRMWARE_VERSION_NAME, SENSOR_LAST_CHECKIN_NAME, SENSOR_LAST_UPDATE_NAME
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
            EinkCalendarDeviceStatusSensor(coordinator, entry),
            EinkCalendarDeviceEtagSensor(coordinator, entry),
            EinkCalendarCheckinCountSensor(coordinator, entry),
        ]
    )


def _device_identifiers(entry: ConfigEntry) -> set:
    mac = entry.data.get(CONF_MAC_ADDRESS)
    return {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)}


class EinkCalendarLastUpdateSensor(SensorEntity):
    """Sensor showing when the display image last changed.

    Listens to coordinator updates (render path sets last_image_change),
    but only writes state when the value actually changes.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} {SENSOR_LAST_UPDATE_NAME.replace('_', ' ').title()}"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_UPDATE_NAME}"
        self._attr_device_info = {"identifiers": _device_identifiers(entry)}
        self._last_written: datetime | None = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        current = self.coordinator.last_image_change
        if current != self._last_written:
            self._last_written = current
            self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_image_change


class EinkCalendarLastCheckinSensor(SensorEntity):
    """Sensor showing last time the ESP32 checked in.

    Only updates on actual device check-ins, not coordinator data refreshes.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:access-point-check"

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Last Check-in"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_CHECKIN_NAME}"
        self._attr_device_info = {"identifiers": _device_identifiers(entry)}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.on_checkin(self._handle_checkin))

    def _handle_checkin(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_checkin


class EinkCalendarFirmwareVersionSensor(SensorEntity):
    """Sensor showing the ESP32's firmware version.

    Only updates on actual device check-ins, not coordinator data refreshes.
    """

    _attr_icon = "mdi:chip"

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Firmware Version"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_FIRMWARE_VERSION_NAME}"
        self._attr_device_info = {"identifiers": _device_identifiers(entry)}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.on_checkin(self._handle_checkin))

    def _handle_checkin(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self.coordinator.firmware_version


class EinkCalendarDeviceStatusSensor(SensorEntity):
    """Sensor showing the device status (healthy, overdue, error, etc.).

    Only updates on actual device check-ins or overdue evaluations.
    """

    _STATUS_ICONS = {
        "healthy": "mdi:check-circle",
        "updating_firmware": "mdi:cellphone-arrow-down",
        "rapid_checkin": "mdi:speedometer",
        "overdue": "mdi:clock-alert",
        "unknown": "mdi:help-circle",
    }

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Device Status"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_DEVICE_STATUS_NAME}"
        self._attr_device_info = {"identifiers": _device_identifiers(entry)}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.on_checkin(self._handle_checkin))

    def _handle_checkin(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self.coordinator.device_status

    @property
    def icon(self) -> str:
        status = self.coordinator.device_status
        if status.startswith("error"):
            return "mdi:alert"
        return self._STATUS_ICONS.get(status, "mdi:help-circle")


class EinkCalendarDeviceEtagSensor(SensorEntity):
    """Sensor showing the device's current ETag.

    Only updates on actual device check-ins.
    """

    _attr_icon = "mdi:tag"

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Device ETag"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_DEVICE_ETAG_NAME}"
        self._attr_device_info = {"identifiers": _device_identifiers(entry)}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.on_checkin(self._handle_checkin))

    def _handle_checkin(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self.coordinator.device_etag


class EinkCalendarCheckinCountSensor(SensorEntity):
    """Sensor showing the total number of device check-ins.

    Only updates on actual device check-ins.
    """

    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._attr_name = f"{entry.data.get(CONF_DEVICE_NAME, 'E-Ink Calendar')} Check-in Count"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_CHECKIN_COUNT_NAME}"
        self._attr_device_info = {"identifiers": _device_identifiers(entry)}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.on_checkin(self._handle_checkin))

    def _handle_checkin(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return self.coordinator.checkin_count

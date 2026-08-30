"""Number entity exposing the base check-in interval.

Home Assistant commands the ESP32's sleep interval on every check-in. This
entity owns the *base* value that command is built from, so an automation can
change the cadence without an options-flow round trip. Quiet hours multiply
whatever base is set here (see ``interval_policy``).
"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_NAME,
    CONF_MAC_ADDRESS,
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)
from .coordinator import EinkCalendarDataCoordinator
from .interval_policy import MAX_INTERVAL_MINUTES, MIN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the refresh-interval number from a config entry."""
    coordinator: EinkCalendarDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EinkCalendarRefreshIntervalNumber(coordinator, entry)])


class EinkCalendarRefreshIntervalNumber(RestoreNumber, NumberEntity):
    """The base minutes between device check-ins."""

    _attr_icon = "mdi:timer-cog-outline"
    _attr_native_unit_of_measurement = "min"
    # The wire format is integer minutes and the firmware reads a non-positive
    # value as "absent", so these bounds mirror interval_policy's clamp.
    _attr_native_min_value = MIN_INTERVAL_MINUTES
    _attr_native_max_value = MAX_INTERVAL_MINUTES
    _attr_native_step = 1

    def __init__(
        self, coordinator: EinkCalendarDataCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the number."""
        self.coordinator = coordinator
        self.entry = entry
        name = entry.data.get(CONF_DEVICE_NAME, "E-Ink Calendar")
        self._attr_name = f"{name} Refresh Interval"
        self._attr_unique_id = f"{entry.entry_id}_refresh_interval"
        mac = entry.data.get(CONF_MAC_ADDRESS)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, entry.entry_id)},
        }

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return self._attr_unique_id

    @property
    def native_value(self) -> float:
        """Current base interval, in minutes."""
        return self.coordinator.base_interval_minutes

    @property
    def native_min_value(self) -> float:
        return self._attr_native_min_value

    @property
    def native_max_value(self) -> float:
        return self._attr_native_max_value

    @property
    def native_step(self) -> float:
        return self._attr_native_step

    async def async_set_native_value(self, value: float) -> None:
        """Set a new base interval."""
        self.coordinator.base_interval_minutes = int(value)
        self.async_write_ha_state()
        _LOGGER.debug("Base check-in interval set to %s minutes", int(value))

    async def async_added_to_hass(self) -> None:
        """Restore the value set before the last restart.

        Without this the base silently reverts to the stored option on every
        HA restart, undoing whatever an automation had set.
        """
        await super().async_added_to_hass()

        restored = await self.async_get_last_number_data()
        value = getattr(restored, "native_value", None) if restored else None
        if value is None:
            return

        if not MIN_INTERVAL_MINUTES <= value <= MAX_INTERVAL_MINUTES:
            _LOGGER.warning(
                "Ignoring restored refresh interval %s — outside %s-%s minutes",
                value,
                MIN_INTERVAL_MINUTES,
                MAX_INTERVAL_MINUTES,
            )
            return

        self.coordinator.base_interval_minutes = int(value)

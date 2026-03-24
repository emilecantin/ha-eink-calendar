"""Data update coordinator for E-Paper Calendar."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CALENDARS,
    CONF_WASTE_CALENDARS,
    CONF_WEATHER_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class EinkCalendarDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching calendar and weather data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )
        self.entry = entry
        self._last_render_day: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from calendars and weather."""
        try:
            now = dt_util.now()

            # Check if day has changed (trigger re-render at midnight)
            current_day = now.date()
            if self._last_render_day != current_day:
                self._last_render_day = current_day
                _LOGGER.debug("Day changed, triggering re-render")

            # Fetch calendar events
            calendar_events = await self._fetch_calendar_events()
            waste_events = await self._fetch_waste_calendar_events()

            # Fetch weather data
            weather_data = await self._fetch_weather_data()

            return {
                "calendar_events": calendar_events,
                "waste_events": waste_events,
                "weather_data": weather_data,
                "timestamp": now,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _fetch_calendar_events(self) -> list[dict[str, Any]]:
        """Fetch events from regular calendars."""
        calendar_ids = self.entry.options.get(CONF_CALENDARS, [])
        if not calendar_ids:
            return []

        all_events = []

        # Fetch 6 weeks of events
        start_time = dt_util.start_of_local_day()
        end_time = start_time + timedelta(weeks=6)

        for calendar_id in calendar_ids:
            try:
                # Get calendar state
                calendar_state = self.hass.states.get(calendar_id)
                if not calendar_state:
                    _LOGGER.warning("Calendar %s not found", calendar_id)
                    continue

                # Get calendar icon
                calendar_icon = calendar_state.attributes.get("icon", "mdi:calendar")
                _LOGGER.debug(
                    "Calendar %s icon: %s (from attributes: %s)",
                    calendar_id,
                    calendar_icon,
                    calendar_state.attributes.get("icon"),
                )

                # Call calendar service to get events
                events = await self.hass.services.async_call(
                    "calendar",
                    "get_events",
                    {
                        "entity_id": calendar_id,
                        "start_date_time": start_time.isoformat(),
                        "end_date_time": end_time.isoformat(),
                    },
                    blocking=True,
                    return_response=True,
                )

                # Process events for this calendar
                if calendar_id in events:
                    for event in events[calendar_id].get("events", []):
                        all_events.append(
                            {
                                "calendar_id": calendar_id,
                                "calendar_icon": calendar_icon,
                                "summary": event.get("summary", ""),
                                "start": event.get("start"),
                                "end": event.get("end"),
                                "description": event.get("description", ""),
                                "location": event.get("location", ""),
                            }
                        )

            except Exception as err:
                _LOGGER.error("Error fetching events from %s: %s", calendar_id, err)
                continue

        return all_events

    async def _fetch_waste_calendar_events(self) -> list[dict[str, Any]]:
        """Fetch events from waste collection calendars."""
        calendar_ids = self.entry.options.get(CONF_WASTE_CALENDARS, [])
        if not calendar_ids:
            return []

        all_events = []

        # Fetch 6 weeks of events
        start_time = dt_util.start_of_local_day()
        end_time = start_time + timedelta(weeks=6)

        for calendar_id in calendar_ids:
            try:
                # Get calendar state
                calendar_state = self.hass.states.get(calendar_id)
                if not calendar_state:
                    _LOGGER.warning("Waste calendar %s not found", calendar_id)
                    continue

                # Get calendar icon (the waste type icon)
                calendar_icon = calendar_state.attributes.get("icon", "🗑️")

                # Call calendar service to get events
                events = await self.hass.services.async_call(
                    "calendar",
                    "get_events",
                    {
                        "entity_id": calendar_id,
                        "start_date_time": start_time.isoformat(),
                        "end_date_time": end_time.isoformat(),
                    },
                    blocking=True,
                    return_response=True,
                )

                # Process events for this calendar
                if calendar_id in events:
                    for event in events[calendar_id].get("events", []):
                        all_events.append(
                            {
                                "calendar_id": calendar_id,
                                "calendar_icon": calendar_icon,
                                "summary": event.get("summary", ""),
                                "start": event.get("start"),
                                "end": event.get("end"),
                            }
                        )

            except Exception as err:
                _LOGGER.error(
                    "Error fetching waste events from %s: %s", calendar_id, err
                )
                continue

        return all_events

    async def _fetch_weather_data(self) -> dict[str, Any] | None:
        """Fetch weather forecast data."""
        weather_entity = self.entry.options.get(CONF_WEATHER_ENTITY)
        if not weather_entity:
            return None

        try:
            weather_state = self.hass.states.get(weather_entity)
            if not weather_state:
                _LOGGER.warning("Weather entity %s not found", weather_entity)
                return None

            # In newer Home Assistant versions, forecast must be fetched via service call
            # Try to get forecast via service call first
            forecast = []
            try:
                forecast_response = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {
                        "entity_id": weather_entity,
                        "type": "daily",  # or "hourly" depending on needs
                    },
                    blocking=True,
                    return_response=True,
                )
                if weather_entity in forecast_response:
                    forecast = forecast_response[weather_entity].get("forecast", [])
            except Exception as forecast_err:
                _LOGGER.debug(
                    "Could not fetch forecast via service call: %s", forecast_err
                )
                # Fallback to attributes (for older HA versions)
                forecast = weather_state.attributes.get("forecast", [])

            return {
                "condition": weather_state.state,
                "temperature": weather_state.attributes.get("temperature"),
                "forecast": forecast,
            }

        except Exception as err:
            _LOGGER.error("Error fetching weather data: %s", err)
            return None

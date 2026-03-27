"""Data update coordinator for E-Paper Calendar."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CALENDARS,
    CONF_WASTE_CALENDARS,
    CONF_WASTE_ICON_MAP,
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
            update_interval=None,  # No polling — refreshed on ESP32 check-in
        )
        self.entry = entry
        self._last_render_day: datetime | None = None
        self.last_checkin: datetime | None = None
        self.last_image_change: datetime | None = None
        self.firmware_version: str = "unknown"
        self._cached_render = None
        self._cached_render_timestamp: datetime | None = None
        self._last_etag: str | None = None
        self._force_refresh: bool = False

    def record_checkin(self, firmware_version: str | None = None) -> None:
        """Record a device check-in and notify listeners (sensors)."""
        self.last_checkin = dt_util.now()
        if firmware_version is not None:
            self.firmware_version = firmware_version
        self.async_set_updated_data(self.data)

    def invalidate_render_cache(self) -> None:
        """Clear the cached render so the next request triggers a fresh render."""
        self._cached_render = None
        self._cached_render_timestamp = None

    def force_refresh(self) -> None:
        """Force the ESP32 to re-download bitmaps on the next check-in."""
        self._force_refresh = True
        self.invalidate_render_cache()

    async def async_get_rendered(self):
        """Get cached rendered calendar, re-rendering only when data changes."""
        from .renderer.renderer import render_calendar

        data = self.data
        if not data:
            return None

        data_ts = data.get("timestamp")
        if self._cached_render is not None and self._cached_render_timestamp == data_ts:
            return self._cached_render

        rendered = await self.hass.async_add_executor_job(
            render_calendar,
            data.get("calendar_events", []),
            data.get("waste_events", []),
            data.get("weather_data"),
            data_ts,
            self.entry.options,
        )

        self._cached_render = rendered
        self._cached_render_timestamp = data_ts

        # Track when the image actually changes
        if rendered and rendered.etag != self._last_etag:
            self._last_etag = rendered.etag
            self.last_image_change = dt_util.now()

        return rendered

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

            # On the very first refresh (async_config_entry_first_refresh),
            # HA converts UpdateFailed → ConfigEntryNotReady and retries setup.
            # After that, we must NOT raise UpdateFailed for missing data —
            # it silently keeps stale data/ETag, causing the ESP32 to get
            # 304 Not Modified forever (display never updates).
            # Instead, render with whatever data is available (possibly empty).
            has_calendars = bool(
                self.entry.options.get(CONF_CALENDARS, [])
                or self.entry.options.get(CONF_WASTE_CALENDARS, [])
            )
            expects_weather = bool(self.entry.options.get(CONF_WEATHER_ENTITY))

            if self.data is None:
                # First refresh — fail so HA retries setup
                if has_calendars and not (calendar_events or waste_events):
                    raise UpdateFailed("Calendar entities not ready yet")
                if expects_weather and weather_data is None:
                    raise UpdateFailed("Weather entity not ready yet")
            else:
                # Subsequent refreshes — log warnings but don't fail
                if has_calendars and not (calendar_events or waste_events):
                    _LOGGER.warning(
                        "No calendar events returned — rendering with empty data"
                    )
                if expects_weather and weather_data is None:
                    _LOGGER.warning(
                        "Weather entity not available — rendering without weather"
                    )

            result = {
                "calendar_events": calendar_events,
                "waste_events": waste_events,
                "weather_data": weather_data,
                "timestamp": now,
            }

            # Pre-render so camera/image entities serve instantly
            try:
                from .renderer.renderer import render_calendar

                rendered = await self.hass.async_add_executor_job(
                    render_calendar,
                    calendar_events,
                    waste_events,
                    weather_data,
                    now,
                    self.entry.options,
                )
                self._cached_render = rendered
                self._cached_render_timestamp = now
                if rendered and rendered.etag != self._last_etag:
                    self._last_etag = rendered.etag
                    self.last_image_change = dt_util.now()
            except Exception as render_err:
                _LOGGER.error("Pre-render failed: %s", render_err, exc_info=True)

            return result
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

                # Get calendar icon — check entity registry first (user customizations),
                # then fall back to state attributes, then default
                ent_reg = er.async_get(self.hass)
                entry = ent_reg.async_get(calendar_id)
                calendar_icon = (
                    (entry.icon if entry and entry.icon else None)
                    or calendar_state.attributes.get("icon")
                    or "mdi:calendar"
                )
                calendar_name = calendar_state.attributes.get("friendly_name") or (
                    calendar_id.replace("calendar.", "").replace("_", " ").title()
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
                                "calendar_name": calendar_name,
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

        icon_map = self.entry.options.get(CONF_WASTE_ICON_MAP, {})
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
                        summary = event.get("summary", "")
                        # Look up icon by event summary, fall back to calendar entity icon
                        calendar_icon = icon_map.get(
                            summary,
                            calendar_state.attributes.get("icon", "mdi:trash-can"),
                        )
                        all_events.append(
                            {
                                "calendar_id": calendar_id,
                                "calendar_icon": calendar_icon,
                                "summary": summary,
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
            _LOGGER.debug("No weather entity configured")
            return None

        try:
            weather_state = self.hass.states.get(weather_entity)
            if not weather_state:
                _LOGGER.warning("Weather entity %s not found", weather_entity)
                return None
            _LOGGER.debug("Weather entity %s state: %s", weather_entity, weather_state.state)

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

            _LOGGER.debug(
                "Weather data: condition=%s, temp=%s, forecast_count=%d",
                weather_state.state,
                weather_state.attributes.get("temperature"),
                len(forecast),
            )
            return {
                "condition": weather_state.state,
                "temperature": weather_state.attributes.get("temperature"),
                "forecast": forecast,
            }

        except Exception as err:
            _LOGGER.error("Error fetching weather data: %s", err)
            return None

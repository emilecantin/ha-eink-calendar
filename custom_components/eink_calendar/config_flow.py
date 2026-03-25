"""Config flow for E-Ink Calendar integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_CALENDARS,
    CONF_DEVICE_NAME,
    CONF_FONT_BOLD,
    CONF_FONT_MEDIUM,
    CONF_FONT_REGULAR,
    CONF_LAYOUT,
    CONF_MAC_ADDRESS,
    CONF_REFRESH_INTERVAL,
    CONF_SHOW_LEGEND,
    CONF_WASTE_CALENDARS,
    CONF_WASTE_ICON_MAP,
    CONF_WEATHER_ENTITY,
    DEFAULT_LAYOUT,
    DEFAULT_NAME,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SHOW_LEGEND,
    DOMAIN,
    LAYOUT_LANDSCAPE,
)

DEFAULT_WASTE_ICONS: dict[str, str] = {
    "Ordures": "mdi:trash-can",
    "Recyclage": "mdi:recycle",
    "Compost": "mdi:compost",
}

_LOGGER = logging.getLogger(__name__)


class EinkCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for E-Ink Calendar."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual add (fallback when no physical device present)."""
        if user_input is not None:
            await self.async_set_unique_id(
                user_input[CONF_DEVICE_NAME].lower().replace(" ", "_")
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data={CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME]},
                options={
                    CONF_CALENDARS: [],
                    CONF_WASTE_CALENDARS: [],
                    CONF_WASTE_ICON_MAP: {},
                    CONF_LAYOUT: DEFAULT_LAYOUT,
                    CONF_SHOW_LEGEND: DEFAULT_SHOW_LEGEND,
                    CONF_WEATHER_ENTITY: None,
                    CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
                    CONF_FONT_REGULAR: None,
                    CONF_FONT_MEDIUM: None,
                    CONF_FONT_BOLD: None,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=DEFAULT_NAME): str,
                }
            ),
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery of an ESP32 device."""
        mac = (discovery_info.properties.get("mac") or "").upper()
        if not mac:
            return self.async_abort(reason="no_mac")

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        name = discovery_info.name.split(".")[0]  # e.g., "eink-cal-01:00"
        self._discovery_info = {
            "mac": mac,
            "name": name,
            "firmware_version": discovery_info.properties.get("fw", "unknown"),
            "ip": str(discovery_info.ip_address),
        }
        self.context["title_placeholders"] = {"name": name}

        # Register HTTP views so announce endpoint is available
        from . import ensure_http_views
        ensure_http_views(self.hass)

        return await self.async_step_configure()

    async def async_step_discovery(
        self, discovery_info: dict[str, Any]
    ) -> FlowResult:
        """Handle device discovery from ESP32 announce."""
        mac = discovery_info["mac"]
        name = discovery_info.get("name", f"E-Ink Calendar {mac[-8:]}")

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": name}

        return await self.async_step_configure()

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure the discovered (or manually added) device."""
        if user_input is not None:
            data = {CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME]}
            if self._discovery_info:
                data[CONF_MAC_ADDRESS] = self._discovery_info["mac"]
                data["firmware_version"] = self._discovery_info.get(
                    "firmware_version", "unknown"
                )

            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data=data,
                options={
                    CONF_CALENDARS: user_input.get(CONF_CALENDARS, []),
                    CONF_WASTE_CALENDARS: user_input.get(CONF_WASTE_CALENDARS, []),
                    CONF_WASTE_ICON_MAP: {},
                    CONF_LAYOUT: user_input.get(CONF_LAYOUT, DEFAULT_LAYOUT),
                    CONF_SHOW_LEGEND: user_input.get(
                        CONF_SHOW_LEGEND, DEFAULT_SHOW_LEGEND
                    ),
                    CONF_WEATHER_ENTITY: user_input.get(CONF_WEATHER_ENTITY),
                    CONF_REFRESH_INTERVAL: user_input.get(
                        CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                    ),
                    CONF_FONT_REGULAR: None,
                    CONF_FONT_MEDIUM: None,
                    CONF_FONT_BOLD: None,
                },
            )

        # Pre-fill name from discovery info
        default_name = DEFAULT_NAME
        if self._discovery_info:
            default_name = self._discovery_info.get(
                "name", f"E-Ink Calendar {self._discovery_info['mac'][-8:]}"
            )

        return self.async_show_form(
            step_id="configure",
            description_placeholders={"name": default_name},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=default_name): str,
                    vol.Optional(
                        CONF_CALENDARS, default=[]
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="calendar",
                            multiple=True,
                        ),
                    ),
                    vol.Optional(
                        CONF_WASTE_CALENDARS, default=[]
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="calendar",
                            multiple=True,
                        ),
                    ),
                    vol.Optional(
                        CONF_LAYOUT, default=DEFAULT_LAYOUT
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": "landscape",
                                    "label": "Landscape (recommended)",
                                },
                                {"value": "portrait", "label": "Portrait"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                    vol.Optional(
                        CONF_SHOW_LEGEND, default=DEFAULT_SHOW_LEGEND
                    ): bool,
                    vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="weather",
                        ),
                    ),
                    vol.Optional(
                        CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=1440,
                            step=1,
                            unit_of_measurement="minutes",
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EinkCalendarOptionsFlow:
        """Get the options flow for this handler."""
        return EinkCalendarOptionsFlow(config_entry)


class EinkCalendarOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for E-Ink Calendar."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._main_options: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Main options."""
        if user_input is not None:
            # Convert empty font paths to None
            for font_key in [CONF_FONT_REGULAR, CONF_FONT_MEDIUM, CONF_FONT_BOLD]:
                if font_key in user_input and not user_input[font_key]:
                    user_input[font_key] = None

            # Preserve existing options not present in the form
            merged = dict(self._config_entry.options)
            merged.update(user_input)
            self._main_options = merged

            # If waste calendars are configured, go to icon mapping step
            if user_input.get(CONF_WASTE_CALENDARS):
                return await self.async_step_waste_icons()

            # No waste calendars — save with empty icon map
            user_input[CONF_WASTE_ICON_MAP] = {}
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CALENDARS,
                        default=options.get(CONF_CALENDARS, []),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="calendar",
                            multiple=True,
                        ),
                    ),
                    vol.Optional(
                        CONF_WASTE_CALENDARS,
                        default=options.get(CONF_WASTE_CALENDARS, []),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="calendar",
                            multiple=True,
                        ),
                    ),
                    vol.Optional(
                        CONF_LAYOUT,
                        default=options.get(CONF_LAYOUT, LAYOUT_LANDSCAPE),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": "landscape",
                                    "label": "Landscape (recommended)",
                                },
                                {"value": "portrait", "label": "Portrait"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                    vol.Optional(
                        CONF_SHOW_LEGEND,
                        default=options.get(CONF_SHOW_LEGEND, DEFAULT_SHOW_LEGEND),
                    ): bool,
                    vol.Optional(
                        CONF_WEATHER_ENTITY,
                        default=options.get(CONF_WEATHER_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="weather",
                        ),
                    ),
                    vol.Optional(
                        CONF_REFRESH_INTERVAL,
                        default=options.get(
                            CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=1440,
                            step=1,
                            unit_of_measurement="minutes",
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                    vol.Optional(
                        CONF_FONT_REGULAR,
                        description={
                            "suggested_value": options.get(CONF_FONT_REGULAR) or ""
                        },
                    ): str,
                    vol.Optional(
                        CONF_FONT_MEDIUM,
                        description={
                            "suggested_value": options.get(CONF_FONT_MEDIUM) or ""
                        },
                    ): str,
                    vol.Optional(
                        CONF_FONT_BOLD,
                        description={
                            "suggested_value": options.get(CONF_FONT_BOLD) or ""
                        },
                    ): str,
                }
            ),
        )

    async def _fetch_waste_summaries(
        self, calendar_ids: list[str]
    ) -> set[str]:
        """Fetch unique event summaries from waste calendars."""
        from homeassistant.util import dt as dt_util
        from datetime import timedelta

        summaries: set[str] = set()
        start_time = dt_util.start_of_local_day()
        end_time = start_time + timedelta(weeks=6)

        for calendar_id in calendar_ids:
            try:
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
                if calendar_id in events:
                    for event in events[calendar_id].get("events", []):
                        summary = event.get("summary", "").strip()
                        if summary:
                            summaries.add(summary)
            except Exception as err:
                _LOGGER.warning(
                    "Could not fetch waste events from %s: %s", calendar_id, err
                )

        return summaries

    async def async_step_waste_icons(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Assign icons to waste event types."""
        if user_input is not None:
            # Build icon map from form: icon_<summary> → mdi:icon
            icon_map: dict[str, str] = {}
            for key, value in user_input.items():
                if key.startswith("icon_") and value:
                    summary = key[5:]  # strip "icon_" prefix
                    icon_map[summary] = value

            self._main_options[CONF_WASTE_ICON_MAP] = icon_map
            return self.async_create_entry(title="", data=self._main_options)

        # Fetch unique summaries from the selected waste calendars
        waste_ids = self._main_options.get(CONF_WASTE_CALENDARS, [])
        summaries = await self._fetch_waste_summaries(waste_ids)

        # Merge with any existing icon map keys (in case calendar is empty right now)
        existing_map = self._config_entry.options.get(CONF_WASTE_ICON_MAP, {})
        all_summaries = sorted(summaries | set(existing_map.keys()))

        if not all_summaries:
            # No summaries found — skip this step
            self._main_options[CONF_WASTE_ICON_MAP] = {}
            return self.async_create_entry(title="", data=self._main_options)

        # Build form with one icon selector per summary
        schema_dict: dict[Any, Any] = {}
        for summary in all_summaries:
            default_icon = (
                existing_map.get(summary)
                or DEFAULT_WASTE_ICONS.get(summary)
                or "mdi:trash-can"
            )
            schema_dict[
                vol.Optional(f"icon_{summary}", default=default_icon)
            ] = selector.IconSelector(
                selector.IconSelectorConfig(placeholder=default_icon)
            )

        return self.async_show_form(
            step_id="waste_icons",
            data_schema=vol.Schema(schema_dict),
        )

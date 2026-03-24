"""Config flow for E-Ink Calendar integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
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
    CONF_WEATHER_ENTITY,
    DEFAULT_LAYOUT,
    DEFAULT_NAME,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SHOW_LEGEND,
    DOMAIN,
    LAYOUT_LANDSCAPE,
)

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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Convert empty font paths to None
            for font_key in [CONF_FONT_REGULAR, CONF_FONT_MEDIUM, CONF_FONT_BOLD]:
                if font_key in user_input and not user_input[font_key]:
                    user_input[font_key] = None
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

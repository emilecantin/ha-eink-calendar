"""Config flow for E-Paper Calendar integration."""

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
    CONF_SHOW_LEGEND,
    CONF_WASTE_CALENDARS,
    CONF_WEATHER_ENTITY,
    DEFAULT_LAYOUT,
    DEFAULT_NAME,
    DEFAULT_SHOW_LEGEND,
    DOMAIN,
    LAYOUT_LANDSCAPE,
)

_LOGGER = logging.getLogger(__name__)


class EpcalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for E-Paper Calendar."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Create entry with device name
            await self.async_set_unique_id(
                user_input[CONF_DEVICE_NAME].lower().replace(" ", "_")
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data=user_input,
                options={
                    CONF_CALENDARS: [],
                    CONF_WASTE_CALENDARS: [],
                    CONF_LAYOUT: DEFAULT_LAYOUT,
                    CONF_SHOW_LEGEND: DEFAULT_SHOW_LEGEND,
                    CONF_WEATHER_ENTITY: None,
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EpcalOptionsFlow:
        """Get the options flow for this handler."""
        return EpcalOptionsFlow(config_entry)


class EpcalOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for E-Paper Calendar."""

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

        # Get all calendar entities
        _ = [entity_id for entity_id in self.hass.states.async_entity_ids("calendar")]

        # Get all weather entities
        _ = [entity_id for entity_id in self.hass.states.async_entity_ids("weather")]

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

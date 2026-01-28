"""Services for EPCAL device management."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_AUTHORIZE_DEVICE = "authorize_device"
SERVICE_DENY_DEVICE = "deny_device"
SERVICE_REVOKE_DEVICE = "revoke_device"
SERVICE_TRIGGER_RENDER = "trigger_render"

AUTHORIZE_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)

DENY_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)

REVOKE_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)

TRIGGER_RENDER_SCHEMA = vol.Schema({})


async def async_setup_services(hass: HomeAssistant, entry) -> None:
    """Set up services for EPCAL."""

    async def handle_authorize_device(call: ServiceCall) -> None:
        """Authorize a pending device."""
        device_id = call.data["device_id"]

        pending_devices = hass.data[DOMAIN].get("pending_devices", {})
        if device_id not in pending_devices:
            _LOGGER.error("Device %s not found in pending devices", device_id)
            return

        device_info = pending_devices[device_id]

        # Generate API key
        api_key = secrets.token_hex(32)

        # Register device in device registry
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            manufacturer="EPCAL",
            model="ESP32 E-Paper Display",
            name=f"E-Paper Calendar {device_id[-8:]}",
            sw_version=device_info.get("version", "unknown"),
        )

        # Store authorization
        authorized_devices = hass.data[DOMAIN].setdefault("authorized_devices", {})
        authorized_devices[device_id] = {
            "api_key": api_key,
            "mac_address": device_info["mac_address"],
            "authorized_at": datetime.now(),
            "device_registry_id": device.id,
            "entry_id": entry.entry_id,
        }

        # Remove from pending
        pending_devices.pop(device_id, None)

        # Dismiss notification
        await hass.services.async_call(
            "persistent_notification",
            "dismiss",
            {"notification_id": f"epcal_pair_{device_id}"},
        )

        # Create success notification
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "EPCAL Device Authorized",
                "message": (
                    f"Device `{device_id}` has been authorized.\n\n"
                    f"The device will receive its API key on next connection."
                ),
                "notification_id": f"epcal_auth_{device_id}",
            },
        )

        _LOGGER.info("Device %s authorized", device_id)

    async def handle_deny_device(call: ServiceCall) -> None:
        """Deny a pending device."""
        device_id = call.data["device_id"]

        pending_devices = hass.data[DOMAIN].get("pending_devices", {})
        if device_id not in pending_devices:
            _LOGGER.error("Device %s not found in pending devices", device_id)
            return

        # Move to denied list
        denied_devices = hass.data[DOMAIN].setdefault("denied_devices", {})
        denied_devices[device_id] = {
            "denied_at": datetime.now(),
            "mac_address": pending_devices[device_id]["mac_address"],
        }

        # Remove from pending
        pending_devices.pop(device_id, None)

        # Dismiss notification
        await hass.services.async_call(
            "persistent_notification",
            "dismiss",
            {"notification_id": f"epcal_pair_{device_id}"},
        )

        _LOGGER.info("Device %s denied", device_id)

    async def handle_revoke_device(call: ServiceCall) -> None:
        """Revoke authorization from a device."""
        device_id = call.data["device_id"]

        authorized_devices = hass.data[DOMAIN].get("authorized_devices", {})
        if device_id not in authorized_devices:
            _LOGGER.error("Device %s not found in authorized devices", device_id)
            return

        device_info = authorized_devices[device_id]

        # Remove from authorized list
        authorized_devices.pop(device_id, None)

        # Remove from device registry
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_info.get("device_registry_id"))
        if device:
            device_registry.async_remove_device(device.id)

        _LOGGER.info("Device %s revoked", device_id)

    async def handle_trigger_render(call: ServiceCall) -> None:
        """Trigger a manual render of the calendar."""
        # Get the coordinator for this entry
        coordinator = hass.data[DOMAIN].get(entry.entry_id)
        if not coordinator:
            _LOGGER.error("Coordinator not found for entry %s", entry.entry_id)
            return

        # Force a coordinator refresh to fetch latest data
        await coordinator.async_refresh()

        # Force image entities to re-render by invalidating their cache
        # This is done by updating the coordinator's last_update timestamp
        coordinator.data["force_render"] = datetime.now().isoformat()

        # Notify all image entities to update
        coordinator.async_update_listeners()

        _LOGGER.info("Manual render triggered for entry %s", entry.entry_id)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_AUTHORIZE_DEVICE,
        handle_authorize_device,
        schema=AUTHORIZE_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DENY_DEVICE,
        handle_deny_device,
        schema=DENY_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REVOKE_DEVICE,
        handle_revoke_device,
        schema=REVOKE_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRIGGER_RENDER,
        handle_trigger_render,
        schema=TRIGGER_RENDER_SCHEMA,
    )

    _LOGGER.info("EPCAL services registered")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload EPCAL services."""
    hass.services.async_remove(DOMAIN, SERVICE_AUTHORIZE_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_DENY_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_REVOKE_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_RENDER)

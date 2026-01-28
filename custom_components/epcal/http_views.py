"""HTTP API views for ESP32 device communication."""

from __future__ import annotations

import logging
from datetime import datetime

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EpcalPairView(HomeAssistantView):
    """Handle device pairing requests from ESP32."""

    url = "/api/epcal/pair"
    name = "api:epcal:pair"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle pairing request."""
        try:
            data = await request.json()
            device_id = data.get("device_id")
            mac_address = data.get("mac_address")
            firmware_version = data.get("version", "unknown")

            if not device_id or not mac_address:
                return self.json(
                    {"status": "error", "message": "Missing device_id or mac_address"},
                    status_code=400,
                )

            # Check if already authorized
            authorized_devices = self.hass.data[DOMAIN].get("authorized_devices", {})
            if device_id in authorized_devices:
                return self.json(
                    {
                        "status": "authorized",
                        "api_key": authorized_devices[device_id]["api_key"],
                    }
                )

            # Add to pending devices
            pending_devices = self.hass.data[DOMAIN].setdefault("pending_devices", {})
            pending_devices[device_id] = {
                "mac_address": mac_address,
                "version": firmware_version,
                "timestamp": datetime.now(),
            }

            # Create persistent notification for admin
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EPCAL Device Pairing Request",
                    "message": (
                        f"A new EPCAL device is requesting access:\n\n"
                        f"**Device ID:** `{device_id}`\n"
                        f"**MAC Address:** `{mac_address}`\n"
                        f"**Firmware:** `{firmware_version}`\n\n"
                        f"To authorize this device, go to:\n"
                        f"Settings → Devices & Services → EPCAL\n\n"
                        f"Or use the service:\n"
                        f"`epcal.authorize_device` with device_id: `{device_id}`"
                    ),
                    "notification_id": f"epcal_pair_{device_id}",
                },
            )

            _LOGGER.info("Device pairing request: %s (MAC: %s)", device_id, mac_address)

            return self.json(
                {
                    "status": "pending",
                    "message": "Device awaiting authorization in Home Assistant",
                }
            )

        except Exception as err:
            _LOGGER.error("Error handling pairing request: %s", err)
            return self.json({"status": "error", "message": str(err)}, status_code=500)


class EpcalStatusView(HomeAssistantView):
    """Check device authorization status."""

    url = "/api/epcal/status/{device_id}"
    name = "api:epcal:status"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request, device_id: str) -> web.Response:
        """Get device status."""
        try:
            # Check if authorized
            authorized_devices = self.hass.data[DOMAIN].get("authorized_devices", {})
            if device_id in authorized_devices:
                return self.json(
                    {
                        "status": "authorized",
                        "api_key": authorized_devices[device_id]["api_key"],
                    }
                )

            # Check if pending
            pending_devices = self.hass.data[DOMAIN].get("pending_devices", {})
            if device_id in pending_devices:
                return self.json({"status": "pending"})

            # Check if denied
            denied_devices = self.hass.data[DOMAIN].get("denied_devices", {})
            if device_id in denied_devices:
                return self.json({"status": "denied"})

            # Unknown device
            return self.json(
                {"status": "unknown", "message": "Device not found"}, status_code=404
            )

        except Exception as err:
            _LOGGER.error("Error checking device status: %s", err)
            return self.json({"status": "error", "message": str(err)}, status_code=500)


class EpcalBitmapView(HomeAssistantView):
    """Serve bitmap chunks to authorized ESP32 devices."""

    url = "/api/epcal/bitmap/{device_id}/{layer}"
    name = "api:epcal:bitmap"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(
        self, request: web.Request, device_id: str, layer: str
    ) -> web.Response:
        """Serve bitmap layer."""
        try:
            # Verify API key
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                return web.Response(text="Missing X-API-Key header", status=401)

            # Check authorization
            authorized_devices = self.hass.data[DOMAIN].get("authorized_devices", {})
            if device_id not in authorized_devices:
                _LOGGER.warning(
                    "Unauthorized device attempted to fetch bitmap: %s", device_id
                )
                return web.Response(text="Device not authorized", status=403)

            if authorized_devices[device_id]["api_key"] != api_key:
                _LOGGER.warning("Invalid API key for device: %s", device_id)
                return web.Response(text="Invalid API key", status=403)

            # Validate layer name
            valid_layers = ["black_top", "black_bottom", "red_top", "red_bottom"]
            if layer not in valid_layers:
                return web.Response(
                    text=f"Invalid layer. Must be one of: {', '.join(valid_layers)}",
                    status=400,
                )

            # Get the image entity for this device and layer
            # First, find the config entry for this device
            entry_id = authorized_devices[device_id].get("entry_id")
            if not entry_id:
                _LOGGER.error("No entry_id found for device %s", device_id)
                return web.Response(text="Device configuration not found", status=500)

            # Construct entity_id
            entity_id = f"image.{device_id}_{layer}"

            # Get image entity
            entity_reg = self.hass.helpers.entity_registry.async_get(self.hass)
            entity_entry = entity_reg.async_get(entity_id)

            if not entity_entry:
                _LOGGER.error("Entity not found: %s", entity_id)
                return web.Response(
                    text=f"Image entity not found: {entity_id}", status=404
                )

            # Get the image component
            image_component = self.hass.data.get("image")
            if not image_component:
                return web.Response(text="Image component not loaded", status=500)

            # Get image bytes
            image_data = await image_component.async_get_image(entity_id)
            if not image_data:
                return web.Response(text="Failed to get image data", status=500)

            _LOGGER.debug(
                "Serving bitmap %s to device %s (%d bytes)",
                layer,
                device_id,
                len(image_data.content),
            )

            # Return binary data
            return web.Response(
                body=image_data.content,
                content_type="application/octet-stream",
                headers={
                    "Content-Length": str(len(image_data.content)),
                },
            )

        except Exception as err:
            _LOGGER.error("Error serving bitmap: %s", err, exc_info=True)
            return web.Response(text=f"Internal server error: {err}", status=500)


def setup_http_views(hass: HomeAssistant) -> None:
    """Register HTTP views."""
    hass.http.register_view(EpcalPairView(hass))
    hass.http.register_view(EpcalStatusView(hass))
    hass.http.register_view(EpcalBitmapView(hass))

    _LOGGER.info("EPCAL HTTP API views registered")

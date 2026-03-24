"""HTTP API views for ESP32 device communication."""

from __future__ import annotations

import hashlib
import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import CONF_MAC_ADDRESS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EinkCalendarAnnounceView(HomeAssistantView):
    """Handle device announce requests from ESP32."""

    url = "/api/eink_calendar/announce"
    name = "api:eink_calendar:announce"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle announce request from ESP32."""
        try:
            data = await request.json()
            mac = data.get("mac")
            name = data.get("name", "E-Ink Calendar")
            firmware_version = data.get("firmware_version", "unknown")

            if not mac:
                return self.json(
                    {"status": "error", "message": "Missing mac"},
                    status_code=400,
                )

            # Normalize MAC address
            mac = mac.upper()

            # Check if MAC matches an existing config entry
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(CONF_MAC_ADDRESS) == mac:
                    # Device is already configured
                    return self.json(
                        {
                            "status": "configured",
                            "entry_id": entry.entry_id,
                            "refresh_interval": entry.options.get(
                                "refresh_interval", 15
                            ),
                            "endpoints": {
                                "black_top": f"/api/eink_calendar/bitmap/{entry.entry_id}/black_top",
                                "black_bottom": f"/api/eink_calendar/bitmap/{entry.entry_id}/black_bottom",
                                "red_top": f"/api/eink_calendar/bitmap/{entry.entry_id}/red_top",
                                "red_bottom": f"/api/eink_calendar/bitmap/{entry.entry_id}/red_bottom",
                                "check": f"/api/eink_calendar/bitmap/{entry.entry_id}/check",
                            },
                        }
                    )

            # Check if there's already a pending discovery flow for this MAC
            for flow in self.hass.config_entries.flow.async_progress():
                if (
                    flow["handler"] == DOMAIN
                    and flow.get("context", {}).get("unique_id") == mac
                ):
                    return self.json({"status": "pending"})

            # Start a new discovery flow
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "discovery"},
                data={
                    "mac": mac,
                    "name": name,
                    "firmware_version": firmware_version,
                    "ip": request.remote,
                },
            )

            _LOGGER.info(
                "New device announced: %s (MAC: %s, FW: %s)",
                name,
                mac,
                firmware_version,
            )

            return self.json({"status": "pending"})

        except Exception as err:
            _LOGGER.error("Error handling announce request: %s", err)
            return self.json(
                {"status": "error", "message": str(err)}, status_code=500
            )


class EinkCalendarBitmapView(HomeAssistantView):
    """Serve bitmap chunks to configured ESP32 devices."""

    url = "/api/eink_calendar/bitmap/{entry_id}/{layer}"
    name = "api:eink_calendar:bitmap"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(
        self, request: web.Request, entry_id: str, layer: str
    ) -> web.Response:
        """Serve bitmap layer."""
        try:
            # Find the config entry
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN:
                return web.Response(text="Unknown device", status=404)

            # Verify MAC address from request header
            request_mac = request.headers.get("X-MAC", "").upper()
            entry_mac = entry.data.get(CONF_MAC_ADDRESS, "")

            # Only require MAC check if the entry has a MAC (discovered devices)
            if entry_mac and request_mac != entry_mac:
                _LOGGER.warning(
                    "MAC mismatch for entry %s: got %s, expected %s",
                    entry_id,
                    request_mac,
                    entry_mac,
                )
                return web.Response(text="Unauthorized", status=403)

            # Handle ETag check endpoint
            if layer == "check":
                coordinator = self.hass.data[DOMAIN].get(entry_id)
                if not coordinator or not coordinator.data:
                    return web.Response(text="No data", status=503)

                etag = self._compute_etag(coordinator)
                if_none_match = request.headers.get("If-None-Match")
                if if_none_match and if_none_match == etag:
                    return web.Response(status=304)

                return web.Response(
                    status=200,
                    headers={"ETag": etag},
                )

            # Validate layer name
            valid_layers = ["black_top", "black_bottom", "red_top", "red_bottom"]
            if layer not in valid_layers:
                return web.Response(
                    text=f"Invalid layer. Must be one of: {', '.join(valid_layers)}",
                    status=400,
                )

            # Get coordinator
            coordinator = self.hass.data[DOMAIN].get(entry_id)
            if not coordinator:
                return web.Response(text="Device not ready", status=503)

            # Get the image data from the coordinator's cached render
            # We need to trigger a render and get the specific layer
            from .renderer.renderer import render_calendar

            data = coordinator.data
            if not data:
                return web.Response(text="No calendar data available", status=503)

            rendered = await self.hass.async_add_executor_job(
                render_calendar,
                data.get("calendar_events", []),
                data.get("waste_events", []),
                data.get("weather_data"),
                data.get("timestamp"),
                entry.options,
            )

            # Get the appropriate chunk
            chunk = None
            if layer == "black_top":
                chunk = rendered.get_black_top()
            elif layer == "black_bottom":
                chunk = rendered.get_black_bottom()
            elif layer == "red_top":
                chunk = rendered.get_red_top()
            elif layer == "red_bottom":
                chunk = rendered.get_red_bottom()

            if chunk is None:
                return web.Response(text="Failed to render", status=500)

            etag = self._compute_etag(coordinator)

            # Check If-None-Match
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match == etag:
                return web.Response(status=304)

            _LOGGER.debug(
                "Serving bitmap %s for entry %s (%d bytes)",
                layer,
                entry_id,
                len(chunk),
            )

            return web.Response(
                body=chunk,
                content_type="application/octet-stream",
                headers={
                    "Content-Length": str(len(chunk)),
                    "ETag": etag,
                },
            )

        except Exception as err:
            _LOGGER.error("Error serving bitmap: %s", err, exc_info=True)
            return web.Response(text=f"Internal server error: {err}", status=500)

    def _compute_etag(self, coordinator) -> str:
        """Compute ETag from coordinator data timestamp."""
        if coordinator.data and coordinator.data.get("timestamp"):
            ts = str(coordinator.data["timestamp"])
            return hashlib.md5(ts.encode()).hexdigest()
        return ""


def setup_http_views(hass: HomeAssistant) -> None:
    """Register HTTP views."""
    hass.http.register_view(EinkCalendarAnnounceView(hass))
    hass.http.register_view(EinkCalendarBitmapView(hass))

    _LOGGER.info("E-Ink Calendar HTTP API views registered")

"""HTTP API views for ESP32 device communication."""

from __future__ import annotations

import logging
import time

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

import json

from .const import CONF_MAC_ADDRESS, DOMAIN, FIRMWARE_MANAGER_KEY

_LOGGER = logging.getLogger(__name__)


class EinkCalendarAnnounceView(HomeAssistantView):
    """Handle device announce requests from ESP32."""

    url = "/api/eink_calendar/announce"
    name = "api:eink_calendar:announce"
    requires_auth = False

    ANNOUNCE_COOLDOWN = 60  # seconds between new discovery flows per MAC

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass
        self._recent_announces: dict[str, float] = {}  # MAC → timestamp

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
                    # Record check-in and firmware version
                    coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
                    if coordinator:
                        coordinator.record_checkin(firmware_version=firmware_version)

                    _LOGGER.debug(
                        "Announce: MAC=%s configured, entry_id=%s",
                        mac,
                        entry.entry_id,
                    )

                    # Build response
                    response_data = {
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
                            "error": f"/api/eink_calendar/error/{entry.entry_id}",
                        },
                    }

                    # Include OTA info if firmware update available
                    fw_manager = self.hass.data.get(DOMAIN, {}).get(
                        FIRMWARE_MANAGER_KEY
                    )
                    if fw_manager:
                        ota_info = fw_manager.build_ota_info(
                            firmware_version, entry.entry_id
                        )
                        if ota_info:
                            response_data["firmware_update"] = ota_info

                    return self.json(response_data)

            # Check if there's already a pending discovery flow for this MAC
            for flow in self.hass.config_entries.flow.async_progress():
                if (
                    flow["handler"] == DOMAIN
                    and flow.get("context", {}).get("unique_id") == mac
                ):
                    return self.json({"status": "pending"})

            # Evict stale entries from the rate-limit dict
            now = time.monotonic()
            self._recent_announces = {
                k: v
                for k, v in self._recent_announces.items()
                if now - v < self.ANNOUNCE_COOLDOWN
            }

            # Rate-limit new discovery flows per MAC
            last_announce = self._recent_announces.get(mac, 0)
            if now - last_announce < self.ANNOUNCE_COOLDOWN:
                return self.json({"status": "pending"})
            self._recent_announces[mac] = now

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
                {"status": "error", "message": "Internal server error"},
                status_code=500,
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
            _LOGGER.debug(
                "Bitmap request: entry_id=%s, layer=%s", entry_id, layer,
            )

            # Find the config entry
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN:
                _LOGGER.warning("Unknown entry_id: %s", entry_id)
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

            if not entry_mac:
                _LOGGER.debug(
                    "MAC check skipped for manual entry %s", entry_id
                )

            # Get coordinator
            coordinator = self.hass.data.get(DOMAIN, {}).get(entry_id)
            if not coordinator:
                return web.Response(text="Device not ready", status=503)

            # Validate layer name
            valid_layers = [
                "check", "black_top", "black_bottom", "red_top", "red_bottom",
            ]
            if layer not in valid_layers:
                return web.Response(
                    text=f"Invalid layer. Must be one of: {', '.join(valid_layers)}",
                    status=400,
                )

            # On check requests, record check-in and refresh data
            if layer == "check":
                fw_version = request.headers.get("X-Firmware-Version", "")
                coordinator.record_checkin(
                    firmware_version=fw_version if fw_version else None
                )
                await coordinator.async_request_refresh()
                if not coordinator.last_update_success:
                    _LOGGER.warning(
                        "Data refresh failed for entry %s — serving stale data",
                        entry_id,
                    )

            rendered = await coordinator.async_get_rendered()
            if rendered is None:
                return web.Response(text="No calendar data available", status=503)

            etag = rendered.etag
            refresh_interval = str(entry.options.get("refresh_interval", 15))

            # Check endpoint — sync device state
            if layer == "check":
                if_none_match = request.headers.get("If-None-Match")
                image_changed = not (if_none_match and if_none_match == etag)

                # Force refresh overrides ETag match
                if coordinator.consume_force_refresh():
                    image_changed = True

                if if_none_match:
                    coordinator.device_etag = if_none_match

                _LOGGER.info(
                    "Check-in: device_etag=%s, server_etag=%s, match=%s, fw=%s",
                    if_none_match or "(none)", etag, not image_changed, fw_version,
                )

                # Check for firmware update
                fw_manager = self.hass.data.get(DOMAIN, {}).get(
                    FIRMWARE_MANAGER_KEY
                )
                ota_info = None
                if fw_manager and fw_version:
                    ota_info = fw_manager.build_ota_info(
                        fw_version, entry_id
                    )

                # 304 only if nothing to do
                if not image_changed and not ota_info:
                    return web.Response(
                        status=304,
                        headers={"X-Refresh-Interval": refresh_interval},
                    )

                # 200 with JSON body describing what changed
                response_data = {
                    "refresh_interval": int(float(refresh_interval)),
                }
                if image_changed:
                    response_data["etag"] = etag
                if ota_info:
                    response_data["firmware_update"] = ota_info

                return web.Response(
                    text=json.dumps(response_data),
                    content_type="application/json",
                    status=200,
                )

            # Bitmap layer requests — ETag check
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match == etag:
                _LOGGER.info("Bitmap %s: 304 not modified", layer)
                return web.Response(status=304)

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

            _LOGGER.info(
                "Bitmap %s: served 200 (%d bytes)",
                layer,
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
            return web.Response(text="Internal server error", status=500)


class EinkCalendarErrorView(HomeAssistantView):
    """Handle error reports from ESP32 devices."""

    url = "/api/eink_calendar/error/{entry_id}"
    name = "api:eink_calendar:error"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def post(
        self, request: web.Request, entry_id: str
    ) -> web.Response:
        """Handle error report from ESP32."""
        try:
            # Find the config entry
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN:
                _LOGGER.warning("Unknown entry_id: %s", entry_id)
                return web.Response(text="Unknown device", status=404)

            # Verify MAC address from request header
            request_mac = request.headers.get("X-MAC", "").upper()
            entry_mac = entry.data.get(CONF_MAC_ADDRESS, "")

            if entry_mac and request_mac != entry_mac:
                _LOGGER.warning(
                    "MAC mismatch for entry %s: got %s, expected %s",
                    entry_id,
                    request_mac,
                    entry_mac,
                )
                return web.Response(text="Unauthorized", status=403)

            # Parse JSON body
            data = await request.json()
            error = data.get("error", "unknown_error")
            details = data.get("details", "")
            error_msg = f"{error}: {details}" if details else error

            # Get coordinator and record the error (also fires checkin callbacks)
            coordinator = self.hass.data.get(DOMAIN, {}).get(entry_id)
            if coordinator:
                coordinator.record_device_error(error_msg)

            _LOGGER.warning(
                "Device error reported for entry %s: %s", entry_id, error_msg
            )

            return self.json({"status": "ok"})

        except Exception as err:
            _LOGGER.error("Error handling error report: %s", err, exc_info=True)
            return web.Response(text="Internal server error", status=500)


class EinkCalendarFirmwareView(HomeAssistantView):
    """Serve firmware binary to ESP32 devices for OTA updates."""

    url = "/api/eink_calendar/firmware/{entry_id}"
    name = "api:eink_calendar:firmware"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(
        self, request: web.Request, entry_id: str
    ) -> web.Response:
        """Serve firmware binary."""
        try:
            # Find the config entry
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN:
                return web.Response(text="Unknown device", status=404)

            # Verify MAC address from request header
            request_mac = request.headers.get("X-MAC", "").upper()
            entry_mac = entry.data.get(CONF_MAC_ADDRESS, "")
            if entry_mac and request_mac != entry_mac:
                return web.Response(text="Unauthorized", status=403)

            # Get firmware manager
            fw_manager = self.hass.data.get(DOMAIN, {}).get(FIRMWARE_MANAGER_KEY)
            if not fw_manager:
                return web.Response(text="Firmware not available", status=404)

            info = fw_manager.get_firmware_info()
            fw_path = fw_manager.get_firmware_path()
            if not info or not fw_path:
                return web.Response(text="No firmware uploaded", status=404)

            # Read firmware binary
            firmware_data = await self.hass.async_add_executor_job(
                _read_file, fw_path
            )

            # Mark device as updating firmware
            coordinator = self.hass.data.get(DOMAIN, {}).get(entry_id)
            if coordinator:
                coordinator.record_firmware_update()
                _LOGGER.info(
                    "Serving firmware v%s to entry %s (%d bytes)",
                    info["version"], entry_id, len(firmware_data),
                )

            return web.Response(
                body=firmware_data,
                content_type="application/octet-stream",
                headers={
                    "Content-Length": str(len(firmware_data)),
                    "X-Firmware-Version": str(info["version"]),
                },
            )

        except Exception as err:
            _LOGGER.error("Error serving firmware: %s", err, exc_info=True)
            return web.Response(text="Internal server error", status=500)


def _read_file(path: str) -> bytes:
    """Read a file (runs in executor)."""
    with open(path, "rb") as f:
        return f.read()


def setup_http_views(hass: HomeAssistant) -> None:
    """Register HTTP views."""
    hass.http.register_view(EinkCalendarAnnounceView(hass))
    hass.http.register_view(EinkCalendarBitmapView(hass))
    hass.http.register_view(EinkCalendarErrorView(hass))
    hass.http.register_view(EinkCalendarFirmwareView(hass))

    _LOGGER.info("E-Ink Calendar HTTP API views registered")

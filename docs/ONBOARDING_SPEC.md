# Onboarding Flow — Implementation Spec

This document specifies the complete device onboarding experience, step by step,
from first power-on to displaying a calendar. It is the single source of truth
for implementing and testing the flow.

---

## Two Onboarding Paths

### Path A: DIY Builder

User finds the GitHub repo, orders hardware, assembles and flashes the ESP32
themselves. They need:

1. **Hardware guidance** in README — exact parts list with links, wiring diagram,
   soldering notes, case options.
2. **Firmware flashing** — PlatformIO instructions, `pio run -t upload`.
3. **HA integration install** — HACS one-click or manual copy.
4. Then they follow the standard onboarding flow below (Step 1 onwards).

**README must cover**: BOM, wiring, flashing, HA integration install. The firmware
handles everything from first boot.

### Path B: Pre-built Device (bought from you)

User receives a fully assembled device with firmware pre-flashed. When they open the box
and plug it in:

1. Display immediately shows the setup screen with QR codes.
2. They scan a QR to connect their phone to the device's WiFi AP.
3. They enter their home WiFi credentials (and optionally HA URL).
4. The device finds HA, announces itself, and appears in the HA UI.

**The out-of-box experience is 100% guided by the display and captive portal.**
No terminal, no documentation needed. The only prerequisite is that they already
have Home Assistant running with the integration installed.

For Path B, include a **printed card in the box** with:
- "1. Plug in the display"
- "2. Scan the QR code on the screen with your phone"
- "3. Enter your WiFi password"
- "4. Open Home Assistant → Settings → Devices — your calendar will appear"
- "Prerequisite: Install the E-Ink Calendar integration from HACS first"
- QR code linking to the HACS install page / GitHub repo

### What both paths share

Everything from Step 1 onwards is identical. The only difference is how the user
gets to the point of having a powered-on, firmware-loaded ESP32.

---

## Actors

| Actor | Description |
|-------|-------------|
| **ESP32** | E-Ink Calendar device (firmware) |
| **HA** | Home Assistant instance with `eink_calendar` custom component loaded |
| **User** | Person with physical access to the ESP32 and a browser open to HA |

---

## Prerequisites

- HA has the `eink_calendar` integration installed (HACS or manual copy).
- The integration is **not** yet configured (no config entries exist).
- ESP32 is flashed with firmware v1.0.0+.
- ESP32 and HA are on the same LAN (or will be after WiFi setup).

---

## Step 1: First Boot — WiFi Provisioning

**Actor**: ESP32

1. ESP32 powers on. No WiFi credentials in NVS → enters setup mode.
2. Starts WiFiManager AP: SSID `EinkCal-Setup`, IP `192.168.4.1`.
3. Display shows pre-rendered setup screen with:
   - QR code for WiFi network (`WIFI:T:nopass;S:EinkCal-Setup;;`)
   - QR code for config URL (`http://192.168.4.1`)
   - Text: "Scan to connect"
4. User connects phone/laptop to `EinkCal-Setup` WiFi.
5. Captive portal opens (or user navigates to `http://192.168.4.1`).
6. WiFiManager shows a form:
   - **WiFi SSID** (scanned list)
   - **WiFi Password**
   - **HA URL Override** (optional — leave blank for mDNS discovery)
   - **Refresh Interval** (minutes, default 15)
7. User fills in WiFi credentials, clicks Save.
8. `saveParamsCallback()` fires:
   - Stores HA URL override (if given) in `config.ha_url`
   - Stores refresh interval in `config.refresh_interval`
   - Sets `config.configured = true`, `config.discovered = false`
   - Saves to NVS, clears ETag cache
9. WiFiManager connects to the home WiFi network.

**Success**: ESP32 is on the home WiFi. Proceed to Step 2.
**Failure**: WiFi connect fails after 5 retries → display shows "WiFi connection failed" → deep sleep 5 min → retry from Step 1.

### Re-entering setup mode

Hold BOOT button (GPIO0) for 2 seconds during power-on. This forces the config portal
even when WiFi credentials are already saved.

---

## Step 2: Discover and Announce to Home Assistant

**Actor**: ESP32 → HA

Discovery and announce are a single step. The ESP32 finds all HA instances on the
network and tries announcing to each one until one accepts.

### If `config.ha_url` is already set (override or previous discovery)

Announce directly to that URL. Skip mDNS.

### If no URL is set (first boot, no override)

1. Start mDNS responder: `MDNS.begin("eink-cal-XXXX")` (last 5 chars of MAC).
2. Query `_home-assistant._tcp` service.
3. For each discovered instance, POST to `/api/eink_calendar/announce`:
   ```json
   {
     "mac": "AA:BB:CC:DD:EE:FF",
     "name": "EinkCal-EE:FF",
     "firmware_version": "1.0.0"
   }
   ```
4. Stop on first instance that returns `configured` or `pending`.

### Announce response handling (per instance)

HA `EinkCalendarAnnounceView.post()` processes the request:

a. **MAC already has a config entry** → return `configured` (jump to Step 4).
   ESP32 saves this URL as `config.ha_url`, stores endpoints.

b. **MAC has a pending discovery flow** → return `{"status": "pending"}`.
   ESP32 saves this URL, stops trying other instances.

c. **First announce for this MAC** →
   - Fires `config_entries.flow.async_init(DOMAIN, context={"source": "discovery"})`
   - "Discovered: E-Ink Calendar" card appears in **Settings → Devices & Services**
   - Returns `{"status": "pending"}`
   - ESP32 saves this URL, stops trying other instances.

d. **404** → integration not installed on this HA instance. ESP32 saves the URL
   (HA is there, just not ready) and shows "Integration non installee — Installez
   'E-Ink Calendar' dans HACS". Polls every 30s until the endpoint appears.

e. **Other HTTP error** (connection refused, timeout, 5xx) → try next mDNS result.

### When pending

- Display shows: "Waiting for Home Assistant" / "Configure in Settings > Devices"
- Deep sleep 30 seconds
- On wake, announces to the saved URL directly (no mDNS re-discovery needed)

### When no instances found or all fail

- ESP32 does **not** sleep — it stays on WiFi and starts a web server on its DHCP IP
- Display shows a **runtime-generated QR code** pointing to `http://<current_ip>`
  plus instructions: "Home Assistant non trouvé — scannez pour entrer l'adresse"
- User scans QR → opens a simple form in their browser → enters HA URL → submits
- ESP32 saves the URL and immediately retries `discoverAndAnnounce()`
- If no submission within 5 minutes → sleep 5 minutes, retry

This is a distinct state from "no WiFi" (which shows the WiFiManager AP setup screen).
The QR code URL depends on the DHCP-assigned IP, so it must be generated at runtime
using the `ricmoo/QRCode` library rendered directly onto the e-ink display.

### Edge cases

- **Multiple HA instances**: ESP32 tries each one. The first instance that has the
  `eink_calendar` integration loaded will accept the announce. Others return HTTP
  errors (404 — no announce endpoint) and are skipped.
- **HA behind reverse proxy / non-standard port**: User must use the URL override field.
- **mDNS not working**: Some routers block mDNS. The URL override is the fallback.

### Security note

The announce endpoint is unauthenticated. Any device on the LAN can trigger a
discovery flow. This is acceptable because:
- The user must explicitly click "Configure" in HA to complete setup
- MAC-based auth is enforced on all subsequent bitmap requests
- This matches how other HA integrations work (e.g., Chromecast, ESPHome discovery)

---

## Step 3: User Configures Device in Home Assistant

**Actor**: User (in HA UI)

1. User sees notification or goes to **Settings → Devices & Services**.
2. The "Discovered" section shows: **E-Ink Calendar** — "EinkCal-EE:FF".
3. User clicks **Configure**.
4. HA shows the `configure` step form:

   | Field | Type | Default | Required |
   |-------|------|---------|----------|
   | Device Name | text | "EinkCal-EE:FF" (from ESP32) | yes |
   | Calendars | entity selector (calendar, multi) | [] | no |
   | Waste Calendars | entity selector (calendar, multi) | [] | no |
   | Layout | dropdown (Landscape/Portrait) | Landscape | no |
   | Show Legend | boolean | true | no |
   | Weather Entity | entity selector (weather) | — | no |
   | Refresh Interval | number (1–1440 min) | 15 | no |

5. User selects at least one calendar, optionally picks weather entity, clicks Submit.
6. `async_step_configure()` creates the config entry:
   - `data`: `{device_name, mac_address, firmware_version}`
   - `options`: `{calendars, waste_calendars, layout, show_legend, weather_entity, refresh_interval}`
7. `async_setup_entry()` runs:
   - Creates device in device registry (identifier = MAC)
   - Sets up coordinator (fetches calendar + weather data)
   - Registers camera, image, sensor platforms
   - HTTP views are already registered (from `async_setup`)

**Result**: Config entry exists. Next ESP32 announce will get `configured` response.

### Implementation gap — confirmation step

Currently `async_step_discovery` goes straight to the configure form. HA convention
is to show a short confirmation step first ("E-Ink Calendar device found. Set up?")
before showing the full form. This should be added:

```python
async def async_step_discovery(self, discovery_info):
    mac = discovery_info["mac"]
    await self.async_set_unique_id(mac)
    self._abort_if_unique_id_configured()
    self._discovery_info = discovery_info
    self.context["title_placeholders"] = {"name": name}
    # Show confirmation before full config
    return await self.async_step_confirm()

async def async_step_confirm(self, user_input=None):
    if user_input is not None:
        return await self.async_step_configure()
    return self.async_show_form(
        step_id="confirm",
        description_placeholders={"name": self._discovery_info["name"]},
    )
```

Needs matching `strings.json` entry for the confirm step description.

---

## Step 4: ESP32 Receives Configuration

**Actor**: ESP32 → HA

1. ESP32 wakes from deep sleep, reconnects WiFi, announces again.
2. HA finds existing config entry for this MAC → returns:
   ```json
   {
     "status": "configured",
     "entry_id": "abc123...",
     "refresh_interval": 15,
     "endpoints": {
       "black_top": "/api/eink_calendar/bitmap/abc123.../black_top",
       "black_bottom": "/api/eink_calendar/bitmap/abc123.../black_bottom",
       "red_top": "/api/eink_calendar/bitmap/abc123.../red_top",
       "red_bottom": "/api/eink_calendar/bitmap/abc123.../red_bottom",
       "check": "/api/eink_calendar/bitmap/abc123.../check"
     },
     "firmware_update": {
       "version": "1.1.0",
       "url": "/api/eink_calendar/firmware/abc123...",
       "size": 1234567
     }
   }
   ```
   The `firmware_update` field is **optional** — it is only included when a newer
   firmware has been uploaded via the `upload_firmware` service and the device's
   reported `firmware_version` differs from the stored version.
3. ESP32 `announceAndConfigure()` processes:
   - Stores `entry_id` in `config.entry_id`
   - Converts `refresh_interval` to seconds → `config.refresh_interval`
   - Sets `config.discovered = true`
   - Saves config and endpoints to NVS

**Result**: ESP32 knows its endpoints. Proceed to Step 5.

---

## Step 5: Fetch and Display Calendar

**Actor**: ESP32 → HA

1. **ETag check**: GET `{ha_url}{endpoints.check}` with headers:
   - `If-None-Match: {cached_etag}`
   - `X-MAC: AA:BB:CC:DD:EE:FF`

2. HA `EinkCalendarBitmapView.get()` processes:
   - Validates entry_id exists and belongs to `eink_calendar` domain
   - Validates `X-MAC` header matches the config entry's MAC
   - Computes ETag from coordinator data timestamp
   - If ETag matches → return **304 Not Modified**

3. **If 304**: ESP32 skips display refresh, updates `last_check_epoch`, deep sleeps.

4. **If 200** (or no cached ETag): Download all 4 bitmap layers sequentially:
   - GET `{ha_url}{endpoints.black_top}` with `X-MAC` header
   - GET `{ha_url}{endpoints.black_bottom}` with `X-MAC` header
   - GET `{ha_url}{endpoints.red_top}` with `X-MAC` header
   - GET `{ha_url}{endpoints.red_bottom}` with `X-MAC` header

5. For each layer:
   - HA renders the calendar on-demand from coordinator data
   - Returns binary bitmap (~80KB per chunk) with ETag header
   - ESP32 writes chunk directly to display memory via SPI

6. ESP32 triggers display refresh (~37 seconds for tri-color).
7. Saves new ETag to cache.
8. Disconnects WiFi, enters deep sleep for `refresh_interval` seconds.

### Rendering on HA side

When a bitmap request arrives:
1. Get coordinator from `hass.data[DOMAIN][entry_id]`
2. Coordinator has cached data: `{calendar_events, waste_events, weather_data, timestamp}`
3. Call `render_calendar(events, waste, weather, timestamp, options)` in executor
4. `RenderedCalendar` object provides `get_black_top()`, etc. → raw bytes

### Performance consideration

Currently, each layer request triggers a full render. The coordinator should cache
the rendered result and only re-render when the data changes. This is a v1.1 optimization.

---

## Steady State (subsequent boots)

After initial onboarding, the flow simplifies:

```
Boot → WiFi connect
  → Announce (gets "configured" + endpoints)
  → ETag check
    → 304: sleep
    → 200: download 4 chunks → display → sleep
```

The announce call on every boot ensures:
- ESP32 always has fresh endpoints (in case HA restarts and entry_id changes)
- HA knows the device is still alive (for device status tracking)

---

## Error Recovery Matrix

| Situation | ESP32 behavior | Recovery |
|-----------|---------------|----------|
| WiFi connect fails | Show error → sleep 5 min | Retry; hold BOOT to reconfigure |
| mDNS finds nothing | Show QR code to web form on device IP | User enters HA URL manually |
| Announce 404 (no integration) | "Installez E-Ink Calendar dans HACS" → sleep 30s | User installs integration; ESP32 polls |
| Announce other HTTP error | Show error with code → sleep 30s | Retry |
| Announce returns `pending` | Show "Waiting for HA" → sleep 30s | User must configure in HA |
| Bitmap 403 (MAC mismatch) | Log error → sleep | Device may need re-onboarding |
| Bitmap 503 (no data yet) | Retry after sleep | Coordinator is still fetching data |
| Bitmap 500 (render error) | Show error → sleep | Check HA logs |
| Config entry deleted in HA | Next announce → starts new discovery | User reconfigures |

---

## Reconfiguration Scenarios

### User changes calendars/weather in HA
1. User goes to device Options in HA → changes settings → saves.
2. Coordinator refreshes data, new render produces different bitmap.
3. ETag changes.
4. Next ESP32 check → 200 → downloads new bitmaps.

### User deletes device in HA
1. Config entry removed.
2. Next ESP32 announce → MAC not found → new discovery flow starts.
3. "Discovered" card reappears.

### ESP32 moves to different WiFi
1. Hold BOOT button → enter setup mode.
2. Configure new WiFi.
3. `saveParamsCallback` clears `discovered` flag.
4. Re-announce triggers new discovery (or reconnects if same HA).

### User changes HA URL
1. Hold BOOT button → enter setup mode.
2. Enter new URL in HA URL Override field.
3. `saveParamsCallback` clears `discovered` flag and cache.
4. Re-announce to new HA instance.

---

## Display States (what the user sees on the e-ink screen)

The display is the primary communication channel, especially for Path B (pre-built)
users who have no terminal or logs. Every state the device can be in must show a
clear, helpful message on screen.

| State | Display Content | Notes |
|-------|----------------|-------|
| **Setup mode** | QR code (WiFi AP) + QR code (config URL) + "Scan to connect" | Generated at runtime via `ricmoo/QRCode` |
| **Connecting to WiFi** | "Connecting to WiFi..." | Brief, may not be visible (fast transition) |
| **WiFi failed** | "WiFi connection failed" + "Hold BOOT button to reconfigure" | Must tell user how to fix it |
| **Discovering HA** | "Looking for Home Assistant..." | Only shown if mDNS takes time |
| **HA not found** | Runtime QR code → `http://<device_ip>` + "Scannez pour entrer l'adresse" | Web form served on current WiFi IP |
| **Integration not installed** | "Integration non installee" + "Installez 'E-Ink Calendar' dans HACS" | Polls every 30s until endpoint appears |
| **Waiting for HA config** | "Waiting for Home Assistant" + "Open Settings → Devices & Services" | Critical for Path B — user needs to know what to do next |
| **Fetching calendar** | "Updating calendar..." | Brief transition state |
| **Calendar displayed** | The actual rendered calendar | Normal operation |
| **Announce error** | "Connection error (HTTP XXX)" | Technical, but at least gives a code |
| **Render/download error** | "Download failed" + endpoint name | For debugging |

### Implementation notes for display messages

- `display_show_setup_screen()` — runtime QR codes via `ricmoo/QRCode`
- `display_show_message(title, subtitle)` — used for "Waiting for HA", needs to exist
- `display_show_error(message)` — for error states, needs to exist
- All messages should be readable at arm's length (large e-ink text)
- Consider adding a small QR code to the "Waiting for HA" screen that links to
  the HA integrations page (`http://<ha_url>/config/integrations`) — requires knowing
  the HA URL at that point (which we do, from Step 3)

### Critical UX for "Waiting for HA config" state

This is the most confusing moment for Path B users. The device is on their WiFi,
has found HA, but the user hasn't configured it yet. The display message must be
extremely clear:

```
+------------------------------------------+
|                                          |
|     Appareil trouvé!                     |
|                                          |
|     Ouvrez Home Assistant pour           |
|     terminer la configuration:           |
|                                          |
|     Paramètres → Appareils & Services    |
|                                          |
|     [QR CODE → HA integrations page]     |
|                                          |
+------------------------------------------+
```

This requires:
1. Knowing `config.ha_url` (available after Step 3)
2. Runtime QR code generation (or a pre-rendered fallback without QR)
3. French locale (matching the rest of the project)

---

## Future Improvements (not in v1.0.0)

1. **Confirmation step in discovery flow** — show "Device found, set up?" before full config form.
2. **Render caching** — cache rendered bitmap in coordinator, don't re-render per request.
3. **Device status tracking** — record last announce time, show "online/offline" in HA.
4. **Firmware update via HA** — OTA announce protocol is implemented (announce response includes `firmware_update` when an update is available). Remaining: ESP32 firmware must implement the actual OTA download and flash logic.
5. **Runtime QR code on "Waiting" screen** — link to HA integrations page for easy navigation.
6. **Bilingual display messages** — locale selection in WiFiManager or from HA config.

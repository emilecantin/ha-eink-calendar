# E-Ink Calendar Project - Claude Development Guide

## Project Structure

```
epcal/
├── Arduino/epcal/              # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   ├── epcal.ino           # Main sketch with mDNS + announce flow
│   │   ├── config.*            # NVS storage for HA URL, entry ID, endpoints
│   │   ├── diagnostics.h       # Boot stage markers + reset reason names
│   │   ├── display.*           # E-paper display driver
│   │   └── http_client.*       # HTTP client with announce + ETag support
│   └── platformio.ini          # Build config
├── custom_components/eink_calendar/  # Home Assistant custom component
│   ├── __init__.py             # Integration entry point
│   ├── config_flow.py          # Discovery + manual config flow
│   ├── coordinator.py          # Data coordinator (calendar/weather)
│   ├── device_diagnostics.py   # Interprets ESP32 boot diagnostics
│   ├── camera.py               # Preview camera entity
│   ├── image.py                # Bitmap image entities
│   ├── sensor.py               # Sensor entities (last update, last check-in, firmware version, device status + diagnostics)
│   ├── button.py               # Force refresh button entity
│   ├── http_views.py           # Announce API + bitmap serving
│   ├── services.py             # trigger_render + upload_firmware services
│   ├── firmware_manager.py     # Firmware binary storage for OTA
│   └── renderer/               # Python calendar renderer
└── server/                     # Node.js/Express server (reference impl)
    ├── index.ts                # Main server, endpoints, config UI
    ├── renderer.ts             # Canvas-based calendar rendering
    └── fonts/                  # Inter font files for e-paper
```

## Server Development

### CRITICAL: Server Process Management

**THE USER MANAGES ALL SERVER PROCESSES. NEVER START, STOP, OR KILL ANY PROCESSES.**

- The user starts the server themselves
- Nodemon automatically restarts when files change
- NEVER use `kill`, `pkill`, or any process management commands
- NEVER suggest starting or stopping servers
- If you need the server restarted, inform the user and let them do it

### Starting the server (USER ONLY - auto-restarts on changes)

```bash
cd /Users/emilecantin/Documents/Projets/iot/epcal/server
npm run dev > /tmp/epcal-server.log 2>&1 &
```

This uses nodemon which auto-restarts when .ts or .json files change.

### Checking server logs

```bash
tail -f /tmp/epcal-server.log
```

### Finding server process (for information only - DO NOT KILL)

```bash
# Find PIDs (information only)
ps aux | grep "nodemon\|ts-node index.ts" | grep -v grep | awk '{print $2}'
```

### Server endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Config UI (Home Assistant setup, calendar selection) |
| `GET /calendar/preview` | PNG preview of rendered calendar |
| `GET /calendar/black1` | Top half black layer (with ETag) |
| `GET /calendar/black2` | Bottom half black layer |
| `GET /calendar/red1` | Top half red layer |
| `GET /calendar/red2` | Bottom half red layer |
| `GET /calendar/check` | ETag check only (returns 304 if unchanged) |
| `GET /debug` | Debug page with test scenarios |

### Debug modes

Add to `/calendar/preview`: `?debug=true`, `?debug=empty`, `?debug=no-today`, `?debug=sparse`

### TypeScript check

```bash
cd server && npx tsc --noEmit
```

## HA Custom Component

### Domain: `eink_calendar`

### Device Discovery Flow

1. ESP32 boots, connects to WiFi, discovers HA via mDNS
2. ESP32 POSTs to `/api/eink_calendar/announce` with `{mac, name, firmware_version}`
3. HA fires `config_entries.flow.async_init(DOMAIN, context={"source": "discovery"})`
4. "Discovered" card appears in Settings → Integrations
5. User configures calendars, weather, layout in the config flow
6. ESP32 polls `/announce` and gets `{status: "configured", endpoints: {...}}` (plus optional `firmware_update` if OTA available)
7. ESP32 fetches bitmaps from returned endpoints with `X-MAC` header auth

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/eink_calendar/announce` | Device announce (no auth) |
| `GET /api/eink_calendar/bitmap/{entry_id}/{layer}` | Bitmap serving (X-MAC auth) |
| `GET /api/eink_calendar/bitmap/{entry_id}/check` | ETag check (X-MAC auth) |
| `GET /api/eink_calendar/firmware/{entry_id}` | Firmware OTA binary (X-MAC auth) |

### Services

| Service | Description |
|---------|-------------|
| `eink_calendar.trigger_render` | Force a manual re-render |
| `eink_calendar.upload_firmware` | Upload firmware binary (`file_path`, `version`) |

### Testing

```bash
# Run ALL tests (unit + ESP native + integration against HA in Docker)
make test

# Run only Python unit tests
make test-unit

# Run only ESP32 native tests (PlatformIO)
make test-esp

# Run only integration tests (starts HA in Docker automatically)
make test-integration

# Pass extra pytest args
make test-unit ARGS='-k weather'
```

#### Manual API testing

```bash
# Test announce
curl -X POST http://localhost:8123/api/eink_calendar/announce \
  -H "Content-Type: application/json" \
  -d '{"mac":"AA:BB:CC:DD:EE:FF","name":"Kitchen Calendar","firmware_version":"1.0.0"}'

# Test bitmap (after configuring)
curl http://localhost:8123/api/eink_calendar/bitmap/{entry_id}/black_top \
  -H "X-MAC: AA:BB:CC:DD:EE:FF"
```

## ESP32 Firmware

### Building and uploading

```bash
# Build only
make build

# Build and upload via USB
make upload
# or: pio run -d Arduino/epcal -t upload

# Build firmware and bundle into HA integration (for OTA distribution)
make bundle
```

### Monitoring serial output

```bash
make monitor
# or: pio device monitor -d Arduino/epcal -b 115200
```

### Firmware Flow

1. WiFi connect (WiFiManager with "EinkCal-Setup" AP)
2. mDNS discovery for `_home-assistant._tcp`
3. POST `/api/eink_calendar/announce` with MAC/name/firmware (re-announces every boot, even if already configured, to check for OTA)
4. If "pending" → show "Waiting for HA" on display, sleep 30s, retry
5. If "configured" → store entry_id + endpoints
6. If OTA available → download and flash firmware via `http_ota_update()`, reboot (streaming 4KB buffer with watchdog management and stall detection). OTA has a retry limit of 3 attempts tracked in RTC memory to prevent crash loops.
7. ETag check (sends `X-Firmware-Version` + boot diagnostics headers) + fetch bitmaps if changed
8. Download bitmap chunks to LittleFS, then init display and stream from LittleFS to SPI
9. Deep sleep for the interval HA commanded on this check-in (RTC memory), falling back to the NVS baseline

### Debugging a reboot loop (`rapid_checkin`)

`rapid_checkin` is not a firmware state — it's a **derived HA status** meaning the median
check-in interval is under half the interval HA **last commanded** (not the configured
option — see "Dynamic refresh interval" below). It's always a symptom of the ESP32
rebooting on one of its short-sleep paths (30s announce poll, 60s update retry).

The hard part is the window after `updateCalendar()` shuts down WiFi for the display
refresh: the device physically cannot report errors there. Two mechanisms cover it:

- **Boot stage markers** (`diagnostics.h`) — `markStage()` writes progress to RTC memory
  as the boot advances. The *next* boot reports the previous boot's furthest stage as
  `X-Last-Stage`, so an unexpected reset is localised.
- **Deferred error reporting** — `setPendingError()` stashes an error in RTC memory;
  `flushPendingError()` sends it on the next boot, *after* the check request (HA clears
  the device error on each check-in, so reporting before would be overwritten).

Diagnostics sent as headers on every `/check`: `X-Reset-Reason`, `X-Last-Stage`,
`X-Boot-Count`, `X-Free-Heap`, `X-Last-Sleep`, `X-Display-Valid`. All optional —
firmware <1.3.0 omits them.

Read the result from the **Device Status sensor's attributes** in HA (`diagnosis`,
`reset_reason`, `last_stage`, `last_error`, `device_etag`, `server_etag`,
`fingerprint_stuck`, `recent_checkins`), or from the boot banner over `make monitor`.

### Fingerprint (ETag) tracking

The fingerprint the device presents is its `If-None-Match` header — the ETag loaded from
NVS. Every check-in logs `device_etag`, `server_etag` and `etag_match`, because the
relationship between them is diagnostic:

- **Fingerprint identical across ≥3 check-ins and never matching the server** →
  `fingerprint_stuck`. The device re-downloads the same image every cycle and never
  persists the new ETag, which means `display_refresh()` isn't completing.
  Detected by `is_fingerprint_stuck()` in `device_diagnostics.py`.
- **Fingerprint advancing** → refreshes are completing; look elsewhere.
- **`device_etag` is `(none)`** → no stored ETag at all (fresh install, cache cleared, or
  NVS writes failing). Recorded explicitly so it can't be mistaken for "unchanged".
- **`display_valid: false`** → the device has *never* completed a refresh, which
  separates "never worked" from "worked once, broke later".

Note `cache.etag` is set from **chunk 0's** ETag during download, not from the check
response, and is only persisted by `cache_save()` after a successful refresh.

| `reset_reason` | `last_stage` | Meaning |
|---|---|---|
| `brownout` | `display_sent` / `display_init` | Power supply can't sustain the 37s refresh |
| `task_wdt` / `int_wdt` | `display_*` | Display driver hanging (e.g. "M1 Busy") |
| `panic` | any | Crash — the stage localises it |
| `deepsleep` | `downloaded` | Phase-2 LittleFS read failure |
| `deepsleep` | `checked` | Download failing |

Because `cache_save()` only runs *after* a successful `display_refresh()`, any failure
past the download means the ETag is never saved and the calendar is re-downloaded every
cycle — which is what makes these loops fast.

## Dynamic refresh interval

HA tells the device how long to sleep on **every** check-in. There is no separate
protocol for it — the value rides along on the check response:

| Path | Carries the interval as |
|---|---|
| 304 Not Modified | `X-Refresh-Interval` header |
| 200 (something changed) | `refresh_interval` field in the JSON body |
| announce | `refresh_interval` in the JSON body — **the baseline, not the commanded value** |

The firmware collects the header *before* issuing the request (`http_client.cpp`),
because a 304 has no body to parse.

### How the value is computed

`interval_policy.resolve_interval()` — kept free of HA imports so it is unit-testable
in isolation, like `device_diagnostics.py`:

```
effective = base x (multiplier if inside quiet hours else 1)   clamped to 1..1440
```

- **base** — `number.eink_calendar_refresh_interval`, a `RestoreNumber` that survives
  restarts, so automations can change the cadence without an options-flow round trip.
  Falls back to the `refresh_interval` option, then the default.
- **quiet hours** — `quiet_start` / `quiet_end` / `quiet_multiplier` config options.
  The window's start is inclusive and end exclusive, and it wraps midnight
  (23:00→07:00). `start == end` disables it rather than meaning "all day".
- The multiplier is floored at 1: quiet hours may only *slow* check-ins, never speed
  them up, so a misconfigured value can't become a battery-draining fast poll.

The wire format is **integer minutes**, so 1 minute is the finest granularity.
Rounding is half-up, not Python's banker's rounding — `round(22.5)` returning 22
is a surprise, and rounding a sleep interval up is the battery-safe direction.

### Baseline vs commanded — why the split matters

| | Source | Stored | Purpose |
|---|---|---|---|
| **Baseline** | announce response | NVS (`config.refresh_interval`) | Fallback when a check-in fails |
| **Commanded** | check response | RTC (`commandedSleepSeconds`) | This cycle's sleep only |

The announce path deliberately sends the **base**, never the quiet-hours value: the
firmware calls `config_save()` unconditionally on every announce, so a transient
2 a.m. value would persist as the interval the device sleeps for whenever a check-in
fails.

The commanded value lives in RTC memory (survives deep sleep, costs no flash) because
it now changes per cycle. Persisting each change would be ~35k NVS writes/year against
a ~100k-cycle budget. A power-on reset clears RTC memory to 0, which
`effectiveSleepSeconds()` reads as "nothing commanded" and falls back to the baseline.

### Both health detectors track the commanded value

`coordinator.expected_checkin_interval` returns what was last commanded, falling back
to the option before the first check-in. Both detectors depend on it, and both broke
in *opposite* directions when it read the static option:

- `_is_overdue` — a device correctly sleeping 2h during quiet hours was flagged overdue
  after 30 minutes.
- `_is_rapid_checkin` — returning to the 15-minute daytime cadence looked like a reboot
  loop against a 2h expectation.

## Display Specifications

- **Model**: Waveshare 12.48" E-Paper Module (B)
- **Resolution**: 1304 x 984 pixels (landscape)
- **Colors**: Black, White, Red (tri-color)
- **Partial refresh**: NOT SUPPORTED on tri-color
- **Full refresh time**: ~37 seconds

## Critical Technical Notes

### E-Paper Initialization Order

**Always call `DEV_ModuleInit()` before `EPD_12in48B_Init()`**. Missing this causes the display to hang at "M1 Busy".

```cpp
DEV_ModuleInit();      // Initialize SPI/GPIO - REQUIRED
EPD_12in48B_Init();    // Initialize display controller
```

### Bitmap Format

- 1-bit per pixel, MSB first
- 1 = white, 0 = black
- Split into 4 chunks (~80KB each), staged to LittleFS before display update

### Paint Library Parameter Order

`Paint_DrawRectangle(Xstart, Ystart, Xend, Yend, Color, DRAW_FILL, DOT_PIXEL)`

### iCal Date Handling (IMPORTANT — recurring source of bugs)

All-day event end dates from HA are **EXCLUSIVE** per iCal/RFC 5545. The fix
(subtract 1 day) is applied once in `renderer.py:_process_events()`.

**See `docs/calendar-event-handling.md` for the full specification, examples,
and explanation of why this bug keeps recurring.**

### WiFiManager Setup Mode

Hold BOOT button (GPIO0) for 2 seconds during startup to enter config mode. Display shows QR codes for WiFi and config URL.

## Architecture Decisions

1. **Server-side rendering**: HA renders full bitmap, ESP32 just displays
2. **ETag caching**: Skip download on 304 Not Modified (saves battery)
3. **No partial refresh**: Tri-color display doesn't support it
4. **Native device discovery**: ESP32 announces via mDNS, appears as HA discovered device
5. **Per-device config entries**: Each ESP32 gets its own config entry with MAC as unique ID
6. **MAC-based auth**: Bitmap endpoints verify X-MAC header matches config entry
7. **Pre-rendered setup screen**: Avoids runtime QR generation on ESP32
8. **Inter font**: Optimized for e-paper readability
9. **LittleFS chunk staging**: Bitmap chunks are downloaded to LittleFS before display init, avoiding SPI bus conflicts between WiFi and e-paper
10. **OTA with retry limit**: Firmware updates use RTC memory to track attempts (max 3), preventing crash loops from bad firmware
11. **Semver-gated OTA**: HA only offers firmware when the bundled version is strictly newer than the device's reported version (no downgrades)
12. **`make bundle` pipeline**: Builds firmware and copies `.bin` + `.version` into the HA integration directory for OTA distribution

## Development Workflow

### Work Units

All non-trivial changes follow a **work unit** workflow:

1. **Plan** (`/plan-work`): Break features into small, independent work units (<300 lines changed, 1-3 files each), each with tests defined upfront
2. **Implement + Review** (`/work`): Execute a work unit using TDD (red/green/refactor), then automatic review loop
3. **Review** (`/review`): Standalone code review (also used internally by `/work`)

### Review Loop

Every work unit goes through a review cycle:
- A reviewer agent evaluates changes against correctness, conventions, security, and simplicity
- Each finding is categorized: **PASS**, **REWORK** (must fix), or **FLAG_FOR_HUMAN** (needs human decision)
- REWORK items are fixed and re-reviewed automatically (max 3 rounds)
- FLAG_FOR_HUMAN items are presented to the user for decision
- Once review passes: a documentation agent checks if any docs need updating (CLAUDE.md, docs/, inline comments)
- Then: commit to a `<type>/<description>` branch (e.g., `feat/`, `fix/`, `refactor/`), push, and create a PR

### Commands

| Command | Purpose |
|---------|---------|
| `/plan-work [description]` | Break a task into work units |
| `/work [description]` | Implement a work unit with review loop |
| `/review [scope]` | Review changes (defaults to uncommitted) |
| `/create-release` | Push and create a GitHub release |

## Development Guidelines

### Home Assistant Integration

The primary deployment target is the **custom component** (`custom_components/eink_calendar/`). The old Node.js add-on has been removed.

- Test with: `docker-compose up` (starts HA with the component mounted)
- The custom component has its own Python renderer (no Node.js dependency)

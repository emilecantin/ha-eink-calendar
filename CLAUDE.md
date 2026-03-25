# E-Ink Calendar Project - Claude Development Guide

## Project Structure

```
epcal/
├── Arduino/epcal/              # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   ├── epcal.ino           # Main sketch with mDNS + announce flow
│   │   ├── config.*            # NVS storage for HA URL, entry ID, endpoints
│   │   ├── display.*           # E-paper display driver
│   │   └── http_client.*       # HTTP client with announce + ETag support
│   └── platformio.ini          # Build config
├── custom_components/eink_calendar/  # Home Assistant custom component
│   ├── __init__.py             # Integration entry point
│   ├── config_flow.py          # Discovery + manual config flow
│   ├── coordinator.py          # Data coordinator (calendar/weather)
│   ├── camera.py               # Preview camera entity
│   ├── image.py                # Bitmap image entities
│   ├── sensor.py               # Last update sensor
│   ├── http_views.py           # Announce API + bitmap serving
│   ├── services.py             # trigger_render service
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
6. ESP32 polls `/announce` and gets `{status: "configured", endpoints: {...}}`
7. ESP32 fetches bitmaps from returned endpoints with `X-MAC` header auth

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/eink_calendar/announce` | Device announce (no auth) |
| `GET /api/eink_calendar/bitmap/{entry_id}/{layer}` | Bitmap serving (X-MAC auth) |
| `GET /api/eink_calendar/bitmap/{entry_id}/check` | ETag check (X-MAC auth) |

### Services

| Service | Description |
|---------|-------------|
| `eink_calendar.trigger_render` | Force a manual re-render |

### Testing

```bash
# Start HA test environment
docker-compose up

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
cd /Users/emilecantin/Documents/Projets/iot/epcal/Arduino/epcal
pio run -t upload
```

### Monitoring serial output

```bash
pio device monitor -b 115200
```

### Firmware Flow

1. WiFi connect (WiFiManager with "EinkCal-Setup" AP)
2. mDNS discovery for `_home-assistant._tcp`
3. POST `/api/eink_calendar/announce` with MAC/name/firmware
4. If "pending" → show "Waiting for HA" on display, sleep 30s, retry
5. If "configured" → store entry_id + endpoints, fetch bitmaps
6. Display bitmaps, deep sleep for refresh_interval

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
- Split into 4 chunks (~80KB each) for ESP32 memory constraints

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

## Development Guidelines

### Home Assistant Integration

The primary deployment target is the **custom component** (`custom_components/eink_calendar/`). The old Node.js add-on has been removed.

- Test with: `docker-compose up` (starts HA with the component mounted)
- The custom component has its own Python renderer (no Node.js dependency)

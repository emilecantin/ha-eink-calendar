# EPCAL Project - Claude Development Guide

## Project Structure

```
epcal/
├── Arduino/epcal/          # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   ├── epcal.ino       # Main sketch with state machine
│   │   ├── config.*        # NVS storage for WiFi/server config
│   │   ├── display.*       # E-paper display driver
│   │   ├── http_client.*   # HTTP client with ETag support
│   │   └── setup_screen.h  # Pre-rendered setup screen (generated)
│   ├── generate_qr.js      # Generates setup_screen.h with QR codes
│   └── platformio.ini      # Build config
└── server/                 # Node.js/Express server
    ├── index.ts            # Main server, endpoints, config UI
    ├── renderer.ts         # Canvas-based calendar rendering
    ├── fonts/              # Inter font files for e-paper
    └── .epcal-config.json  # Runtime config (gitignored)
```

## Server Development

### Starting the server (PREFERRED - auto-restarts on changes)

```bash
cd /Users/emilecantin/Documents/Projets/iot/epcal/server
npm run dev > /tmp/epcal-server.log 2>&1 &
```

This uses nodemon which auto-restarts when .ts or .json files change.

### Checking server logs

```bash
tail -f /tmp/epcal-server.log
```

### Finding and stopping the server

```bash
# Find PIDs
ps aux | grep "nodemon\|ts-node index.ts" | grep -v grep | awk '{print $2}'

# Kill by specific PID
kill <PIDs>
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

### Regenerating setup screen (QR codes)

Run from server directory to use existing canvas/qrcode dependencies:

```bash
cd server && node ../Arduino/epcal/generate_qr.js
```

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

### iCal Date Handling

All-day events use exclusive end dates:
- Single-day event: start == end (don't subtract)
- Multi-day event: last visible day = end_date - 1

### WiFiManager Setup Mode

Hold BOOT button (GPIO0) for 2 seconds during startup to enter config mode. Display shows QR codes for WiFi and config URL.

## Architecture Decisions

1. **Server-side rendering**: Server renders full bitmap, ESP32 just displays
2. **ETag caching**: Skip download on 304 Not Modified (saves battery)
3. **No partial refresh**: Tri-color display doesn't support it
4. **15-30 minute refresh**: Configurable, balances freshness vs battery
5. **Pre-rendered setup screen**: Avoids runtime QR generation on ESP32
6. **Inter font**: Optimized for e-paper readability

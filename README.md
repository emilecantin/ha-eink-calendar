# EPCAL - E-Paper Calendar

A battery-powered IoT calendar display that shows your Home Assistant calendar events on a large 12.48" tri-color e-paper screen.

## Features

- **Large e-paper display** - Waveshare 12.48" tri-color (black/white/red)
- **Battery optimized** - Deep sleep between updates, ETag caching to skip unnecessary refreshes
- **Server-rendered** - Node.js server fetches calendar data and renders bitmaps
- **Weather integration** - Shows forecast from Home Assistant weather entities
- **Easy setup** - QR codes for WiFi connection and configuration portal
- **French locale** - Day/month names in French
- **Multiple deployment options** - Docker, HA Add-on, or standalone

## Architecture

```
Home Assistant Calendar API
        ↓ (HTTP)
Node.js Server (renders bitmap)
        ↓ (HTTP with ETag caching)
ESP32 Microcontroller
        ↓ (SPI)
Waveshare 12.48" E-Paper Display
```

## Hardware Requirements

- [Waveshare E-Paper ESP32 Driver Board](https://www.waveshare.com/wiki/E-Paper_ESP32_Driver_Board) (or compatible ESP32)
- [Waveshare 12.48" e-Paper Module (B)](https://www.waveshare.com/12.48inch-e-paper-module-b.htm) - tri-color version
- USB cable for programming
- Optional: Battery for portable operation

## Server Installation

Choose one of the following options:

### Option 1: Docker Compose (Recommended)

Best for most users, especially those running Home Assistant in Docker.

```bash
# Clone the repository
git clone https://gitlab.com/emilecantin/epcal.git
cd epcal

# Create config directory
mkdir -p config

# Start the server
docker-compose up -d
```

Visit `http://localhost:4000` to configure.

#### Using Pre-built Image

To use the pre-built image instead of building locally, edit `docker-compose.yml`:

```yaml
services:
  epcal:
    # Comment out the build line:
    # build: ./server
    # Uncomment the image line:
    image: registry.gitlab.com/emilecantin/epcal/addon:latest
    ports:
      - "4000:4000"
    volumes:
      - ./config:/app/config
    environment:
      - CONFIG_PATH=/app/config/.epcal-config.json
      - TZ=America/Toronto
    restart: unless-stopped
```

Then run:
```bash
docker-compose pull
docker-compose up -d
```

### Option 2: Home Assistant Add-on

For users running Home Assistant OS or Supervised installation.

1. In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the menu (⋮) → **Repositories**
3. Add: `https://gitlab.com/emilecantin/epcal`
4. Find "EPCAL - E-Paper Calendar" and click **Install**
5. Start the add-on and open the Web UI

The add-on auto-connects to Home Assistant - no token configuration needed.

> **Note**: This option is not available for Home Assistant Container (Docker) installations.

### Option 3: Run from Source

For development or systems without Docker.

```bash
cd server
npm install
npm run dev   # Development with auto-reload
# or
npm start     # Production
```

Requires Node.js 18+.

## Server Configuration

Visit the web UI at `http://localhost:4000` (or your server's address) to configure:

1. **Home Assistant Connection**
   - Enter your Home Assistant URL (e.g., `http://homeassistant.local:8123`)
   - Create a [Long-Lived Access Token](https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token) in HA (Profile → Long-Lived Access Tokens)
   - Paste the token

2. **Calendars**
   - Select which calendars to display
   - Assign icons (symbols) to each calendar
   - Optionally set custom display names

3. **Layout**
   - Choose Portrait or Landscape orientation
   - Toggle the calendar legend on/off

4. **Weather** (Optional)
   - Select a weather entity for forecast display

Configuration is persisted in `./config/.epcal-config.json` (Docker) or `server/.epcal-config.json` (standalone).

## ESP32 Firmware Setup

The ESP32 firmware is in `Arduino/epcal/` and uses PlatformIO.

### Building and Uploading

```bash
cd Arduino/epcal
pio run -t upload
```

### First-Time Setup

1. Power on the ESP32
2. The display shows QR codes for WiFi and config URL
3. Connect your phone to the "EPCAL-Setup" WiFi network
4. Open `http://192.168.4.1` or scan the config QR code
5. Enter:
   - Your WiFi credentials
   - Server URL (e.g., `http://192.168.1.100:4000`)
   - Refresh interval (in minutes)
6. Click Save

The device will connect and display your calendar.

### Re-entering Setup Mode

Hold the BOOT button for 2 seconds during startup to re-enter configuration mode.

## Display Layout

### Landscape (Recommended)

```
+---------------------------+--------------------------------------------------+
|                           |  LUN  |  MAR  |  MER  |  JEU  |  VEN  |  SAM  |
|  Aujourd'hui              |  Weather + events for each day                   |
|  Date + Weather           |                                                  |
|  Today's events           |                                                  |
|                           |--------------------------------------------------|
|  Legend                   |  À VENIR - Upcoming multi-day events             |
+---------------------------+--------------------------------------------------+
```

### Portrait

```
+---------------------------+
|      Aujourd'hui          |
|      Date + Weather       |
|      Today's events       |
+---------------------------+
|  Week grid (6 days)       |
+---------------------------+
|  À VENIR - Upcoming       |
+---------------------------+
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Configuration UI |
| `GET /calendar/preview` | PNG preview of current render |
| `GET /calendar/check` | ETag check (returns 304 if unchanged) |
| `GET /calendar/black1` | Black layer bitmap (top half) |
| `GET /calendar/black2` | Black layer bitmap (bottom half) |
| `GET /calendar/red1` | Red layer bitmap (top half) |
| `GET /calendar/red2` | Red layer bitmap (bottom half) |
| `GET /debug` | Debug page with test scenarios |

## Debug Modes

Add query parameters to `/calendar/preview`:
- `?debug=true` - Many events (overflow testing)
- `?debug=empty` - No events
- `?debug=no-today` - No events today
- `?debug=sparse` - Few events
- `?debug=no-upcoming` - No upcoming multi-day events

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `4000` |
| `CONFIG_PATH` | Path to config file | `./.epcal-config.json` |
| `TZ` | Timezone (should match HA) | System default |

## Troubleshooting

### Display shows "M1 Busy" and hangs
Ensure `DEV_ModuleInit()` is called before `EPD_12in48B_Init()` in the firmware.

### Weather icons show as boxes
The server needs the Symbola font. In Docker, this is handled automatically. For standalone, install `fonts-symbola` (Debian/Ubuntu) or equivalent.

### Timezone mismatch warning
Set the `TZ` environment variable to match your Home Assistant timezone:
```yaml
environment:
  - TZ=America/Toronto
```

### ESP32 can't connect to server
- Verify the server URL is reachable from the ESP32's network
- Check that port 4000 is not blocked by a firewall
- Try using the IP address instead of hostname
- Ensure both devices are on the same network (or configure routing)

### No events showing
- Ensure at least one calendar is enabled in the web UI
- Check that your HA token has access to calendar entities
- Verify calendars have events in the displayed date range

## Battery Life

The ESP32 uses deep sleep between updates. With ETag caching:
- Most wakes result in 304 Not Modified (~5s active time)
- Full refreshes only when calendar changes (~15s active time)
- Expected battery life: weeks to months with 2000mAh battery

## Project Structure

```
epcal/
├── Arduino/epcal/       # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   ├── epcal.ino    # Main sketch with state machine
│   │   ├── config.*     # NVS storage for configuration
│   │   ├── display.*    # E-paper display driver
│   │   └── http_client.*# HTTP client with ETag support
│   └── platformio.ini
├── server/              # Node.js server
│   ├── index.ts         # Express server, config UI, API
│   ├── renderer.ts      # Canvas-based calendar rendering
│   ├── fonts/           # Inter font files
│   └── Dockerfile       # Standalone Docker build
├── addon/               # Home Assistant Add-on
│   ├── config.yaml      # Add-on metadata
│   ├── Dockerfile       # Multi-arch build
│   └── run.sh           # Startup script
├── docker-compose.yml   # Docker Compose configuration
└── TODO.md              # Project roadmap
```

## Contributing

Issues and merge requests welcome at https://gitlab.com/emilecantin/epcal

## License

MIT

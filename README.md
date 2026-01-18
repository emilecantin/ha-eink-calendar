# EPCAL - E-Paper Calendar

A battery-powered IoT calendar display that shows your Home Assistant calendar events on a large 12.48" tri-color e-paper screen.

## Features

- **Large e-paper display** - Waveshare 12.48" tri-color (black/white/red)
- **Battery optimized** - Deep sleep between updates, ETag caching to skip unnecessary refreshes
- **Server-rendered** - Node.js server fetches calendar data and renders bitmaps
- **Weather integration** - Shows forecast from Home Assistant weather entities
- **Easy setup** - QR codes for WiFi connection and configuration portal
- **French locale** - Day/month names in French

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

- ESP32 development board (tested with ESP32-DevKitC)
- [Waveshare 12.48" e-Paper Module (B)](https://www.waveshare.com/12.48inch-e-paper-module-b.htm) - tri-color version
- USB cable for programming
- Optional: Battery for portable operation

## Software Requirements

### Server
- Node.js 18+
- Home Assistant with calendar entities
- Long-lived access token for Home Assistant API

### ESP32
- PlatformIO (VS Code extension or CLI)
- Waveshare e-Paper library (in `~/Documents/Arduino/libraries`)

## Setup

### 1. Server Setup (Docker)

```bash
docker-compose up -d
```

Visit `http://localhost:4000` to configure:
- Home Assistant URL and long-lived access token
- Select calendars to display
- Assign icons and display names to calendars
- Select weather entity for forecast

Configuration is persisted in `./config/.epcal-config.json`.

#### Alternative: Run without Docker

```bash
cd server
npm install
npm start
```

### 2. ESP32 Setup

```bash
cd Arduino/epcal
pio run -t upload
```

On first boot (or hold BOOT button for 2 seconds to re-enter setup):
1. Display shows QR codes for WiFi and config URL
2. Connect phone to "EPCAL-Setup" WiFi network
3. Open `http://192.168.4.1` or scan the config QR code
4. Enter your WiFi credentials, server URL, and refresh interval
5. Click Save

The device will connect and display your calendar.

## Display Layout

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

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Configuration UI |
| `GET /calendar/preview` | PNG preview of current render |
| `GET /calendar/black1` | Black layer bitmap (top half) |
| `GET /calendar/black2` | Black layer bitmap (bottom half) |
| `GET /calendar/red1` | Red layer bitmap (top half) |
| `GET /calendar/red2` | Red layer bitmap (bottom half) |
| `GET /calendar/check` | ETag check (returns 304 if unchanged) |
| `GET /debug` | Debug page with test scenarios |

## Debug Modes

Add query parameters to `/calendar/preview`:
- `?debug=true` - Many events (overflow testing)
- `?debug=empty` - No events
- `?debug=no-today` - No events today
- `?debug=sparse` - Few events
- `?debug=no-upcoming` - No upcoming multi-day events

## Configuration

### ESP32 Settings

Hold the BOOT button for 2 seconds during startup to enter configuration mode. This allows changing:
- WiFi network and password
- Calendar server URL
- Refresh interval (in minutes)

### Server Settings

Edit via web UI at `http://localhost:4000` or directly in `server/.epcal-config.json`.

## Battery Life

The ESP32 uses deep sleep between updates. With ETag caching:
- Most wakes result in 304 Not Modified (~5s active time)
- Full refreshes only when calendar changes (~15s active time)
- Expected battery life: weeks to months with 2000mAh battery

## License

MIT

# E-Ink Calendar Display

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=emilecantin&repository=ha-eink-calendar&category=integration)

A battery-powered IoT calendar display that shows your Home Assistant calendar events on a large 12.48" tri-color e-paper screen.

## Features

- **Large e-paper display** - Waveshare 12.48" tri-color (black/white/red)
- **Battery optimized** - Deep sleep between updates, ETag caching to skip unnecessary refreshes
- **Home Assistant integration** - Native custom component with Python renderer
- **Native device discovery** - ESP32 auto-discovers HA via mDNS, appears as a discovered device
- **Weather integration** - Shows forecast from Home Assistant weather entities
- **Easy setup** - QR codes for WiFi connection, auto-discovery for HA pairing
- **French locale** - Day/month names in French

## Architecture

```
Home Assistant Calendar API
        | (native HA API)
E-Ink Calendar Custom Component (renders bitmap)
        | (HTTP with ETag caching + MAC auth)
ESP32 Microcontroller (mDNS discovery + announce)
        | (SPI)
Waveshare 12.48" E-Paper Display
```

### Device Discovery Flow

```
ESP32 boots → WiFi connect → mDNS lookup (_home-assistant._tcp)
  → POST /api/eink_calendar/announce {mac, name, firmware_version}

Home Assistant receives announce:
  → New device: "Discovered" card in Settings → Integrations
  → Already configured: returns bitmap endpoints

User clicks Configure → selects calendars, weather, layout
  → ESP32 polls announce → gets endpoints → fetches bitmaps → displays
```

## Hardware Requirements

- [Waveshare E-Paper ESP32 Driver Board](https://www.waveshare.com/wiki/E-Paper_ESP32_Driver_Board) (or compatible ESP32)
- [Waveshare 12.48" e-Paper Module (B)](https://www.waveshare.com/12.48inch-e-paper-module-b.htm) - tri-color version
- USB cable for programming
- Optional: Battery for portable operation

## Installation

### Home Assistant Custom Component

1. Copy `custom_components/eink_calendar/` into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** > **Devices & Services** > **Add Integration**
4. Search for "E-Ink Calendar" and follow the configuration wizard

Or install via HACS using the badge above.

### Configuration

The integration is configured through the HA UI:

1. **Calendars** - Select which calendars to display
2. **Waste Calendars** - Select waste collection calendars (icon-only display)
3. **Layout** - Choose Portrait or Landscape orientation
4. **Weather** (Optional) - Select a weather entity for forecast display
5. **Refresh Interval** - How often to re-render (in minutes)

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
3. Connect your phone to the "EinkCal-Setup" WiFi network
4. Open `http://192.168.4.1` or scan the config QR code
5. Enter your WiFi credentials (HA URL override is optional - mDNS discovery is automatic)
6. Click Save

The ESP32 will:
- Connect to WiFi
- Discover Home Assistant via mDNS
- Announce itself to HA
- A "Discovered" card appears in HA Settings > Integrations
- After you configure it in HA, the calendar displays automatically

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
|  Legend                   |  A VENIR - Upcoming multi-day events             |
+---------------------------+--------------------------------------------------+
```

## Troubleshooting

### Display shows "M1 Busy" and hangs
Ensure `DEV_ModuleInit()` is called before `EPD_12in48B_Init()` in the firmware.

### ESP32 can't find Home Assistant
- Ensure mDNS is working on your network (HA must be discoverable via `_home-assistant._tcp`)
- As a fallback, enter the HA URL manually in the WiFi setup portal
- Ensure both devices are on the same network

### No events showing
- Ensure at least one calendar is selected in the integration config
- Verify calendars have events in the displayed date range

## Battery Life

The ESP32 uses deep sleep between updates. With ETag caching:
- Most wakes result in 304 Not Modified (~5s active time)
- Full refreshes only when calendar changes (~15s active time)
- Expected battery life: weeks to months with 2000mAh battery

## Project Structure

```
epcal/
├── Arduino/epcal/                  # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   ├── epcal.ino              # Main sketch with mDNS + announce flow
│   │   ├── config.*               # NVS storage for HA URL, endpoints
│   │   ├── display.*              # E-paper display driver
│   │   └── http_client.*          # HTTP client with announce + ETag
│   └── platformio.ini
├── custom_components/eink_calendar/ # Home Assistant custom component
│   ├── renderer/                   # Python calendar renderer
│   ├── config_flow.py             # Discovery + manual config flow
│   ├── http_views.py              # Announce + bitmap API views
│   └── coordinator.py             # Data coordinator
├── server/                         # Node.js server (reference impl)
│   ├── index.ts                   # Express server, config UI, API
│   ├── renderer.ts                # Canvas-based calendar rendering
│   └── fonts/                     # Inter font files
└── docker-compose.yml             # HA test environment
```

## Development

### Visual Regression Testing

Run the complete test suite to compare TypeScript and Python renderer output:

```bash
python3 scripts/run_tests.py
```

## Contributing

Issues and pull requests welcome at https://github.com/emilecantin/ha-eink-calendar

## License

MIT

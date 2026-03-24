# EPCAL - E-Paper Calendar

A battery-powered IoT calendar display that shows your Home Assistant calendar events on a large 12.48" tri-color e-paper screen.

## Features

- **Large e-paper display** - Waveshare 12.48" tri-color (black/white/red)
- **Battery optimized** - Deep sleep between updates, ETag caching to skip unnecessary refreshes
- **Home Assistant integration** - Native custom component with Python renderer
- **Weather integration** - Shows forecast from Home Assistant weather entities
- **Easy setup** - QR codes for WiFi connection and configuration portal
- **French locale** - Day/month names in French

## Architecture

```
Home Assistant Calendar API
        ↓ (native HA API)
EPCAL Custom Component (renders bitmap)
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

## Installation

### Home Assistant Custom Component

1. Copy `custom_components/epcal/` into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "EPCAL" and follow the configuration wizard

### Configuration

The integration is configured through the HA UI:

1. **Calendars** - Select which calendars to display, assign icons
2. **Layout** - Choose Portrait or Landscape orientation
3. **Weather** (Optional) - Select a weather entity for forecast display

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

## Troubleshooting

### Display shows "M1 Busy" and hangs
Ensure `DEV_ModuleInit()` is called before `EPD_12in48B_Init()` in the firmware.

### ESP32 can't connect to Home Assistant
- Verify the HA URL is reachable from the ESP32's network
- Try using the IP address instead of hostname
- Ensure both devices are on the same network (or configure routing)

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
├── Arduino/epcal/       # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   ├── epcal.ino    # Main sketch with state machine
│   │   ├── config.*     # NVS storage for configuration
│   │   ├── display.*    # E-paper display driver
│   │   └── http_client.*# HTTP client with ETag support
│   └── platformio.ini
├── custom_components/epcal/  # Home Assistant custom component
│   ├── renderer/            # Python calendar renderer
│   ├── config_flow.py       # UI configuration wizard
│   └── coordinator.py       # Data coordinator
├── server/                  # Node.js server (reference impl)
│   ├── index.ts             # Express server, config UI, API
│   ├── renderer.ts          # Canvas-based calendar rendering
│   └── fonts/               # Inter font files
└── docker-compose.yml       # HA test environment
```

## Development

### Visual Regression Testing

Run the complete test suite to compare TypeScript and Python renderer output:

```bash
python3 scripts/run_tests.py
```

See [TESTING.md](TESTING.md) for detailed testing documentation.

### Border Alignment

The Python renderer has been updated to match Canvas border behavior exactly. See [BORDER_FIX_RESULTS.md](BORDER_FIX_RESULTS.md) for technical details.

## Contributing

Issues and merge requests welcome at https://gitlab.com/emilecantin/epcal

## License

MIT

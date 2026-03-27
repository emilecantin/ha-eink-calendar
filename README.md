# E-Ink Calendar Display

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=emilecantin&repository=ha-eink-calendar&category=integration)

A battery-powered IoT calendar display that shows your Home Assistant calendar events on a large 12.48" tri-color e-paper screen.

## Features

- **Large e-paper display** — Waveshare 12.48" tri-color (black/white/red)
- **Battery optimized** — Deep sleep between updates, ETag caching to skip unnecessary refreshes
- **Native HA integration** — Custom component with Python renderer, no external server needed
- **Device discovery** — ESP32 auto-discovers HA via mDNS, appears as a discovered device
- **Weather integration** — Shows daily forecast from any HA weather entity
- **Waste collection** — Icon-only display for waste/recycling calendars
- **Multi-language** — French and English, configurable per device
- **Multi-device** — Each ESP32 gets its own config entry with independent settings

## Hardware Requirements

- [Waveshare E-Paper ESP32 Driver Board](https://www.waveshare.com/wiki/E-Paper_ESP32_Driver_Board) (or compatible ESP32)
- [Waveshare 12.48" e-Paper Module (B)](https://www.waveshare.com/12.48inch-e-paper-module-b.htm) — tri-color version
- USB cable for programming
- Optional: battery for portable operation

## Installation

### Home Assistant Integration

Install via HACS using the badge above, or manually:

1. Copy `custom_components/eink_calendar/` to your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** > **Devices & Services** > **Add Integration**
4. Search for "E-Ink Calendar" and follow the setup wizard

### Configuration

Each device is configured through the HA UI with these options:

| Option | Description |
|--------|-------------|
| **Calendars** | Which calendar entities to display with full event details |
| **Waste Calendars** | Calendar entities shown as icons only (e.g., garbage/recycling) |
| **Language** | Display language — French or English |
| **Layout** | Landscape (recommended) or Portrait |
| **Show Legend** | Show calendar icon legend at the bottom |
| **Weather Entity** | Optional weather entity for daily forecast |
| **Refresh Interval** | How often the ESP32 checks for updates (minutes) |
| **Custom Fonts** | Optional paths to custom TTF fonts (Regular, Medium, Bold) |

All options can be changed later in **Settings > Devices & Services > E-Ink Calendar > Configure**.

### Entities Created

Each device creates:

| Entity | Description |
|--------|-------------|
| `camera.{name}_preview` | Full-color PNG preview of the calendar |
| `image.{name}_black_layer_top` | Top half of the black bitmap layer |
| `image.{name}_black_layer_bottom` | Bottom half of the black bitmap layer |
| `image.{name}_red_layer_top` | Top half of the red bitmap layer |
| `image.{name}_red_layer_bottom` | Bottom half of the red bitmap layer |
| `sensor.{name}_last_update` | Timestamp of the last render |
| `sensor.{name}_last_checkin` | Timestamp of the last ESP32 check-in |

## ESP32 Firmware

The firmware is in `Arduino/epcal/` and uses PlatformIO.

### Building and Uploading

```bash
cd Arduino/epcal
pio run -t upload
```

### First-Time Setup

1. Power on the ESP32 — the display shows QR codes for WiFi and config URL
2. Connect your phone to the **EinkCal-Setup** WiFi network
3. Open `http://192.168.4.1` or scan the config QR code
4. Enter your WiFi credentials and click Save

The ESP32 will automatically:
- Connect to WiFi
- Discover Home Assistant via mDNS
- Announce itself — a "Discovered" card appears in **Settings > Integrations**
- After you configure it in HA, the calendar displays automatically

To re-enter setup mode, hold the BOOT button for 2 seconds during startup.

### How Updates Work

1. ESP32 wakes from deep sleep
2. Sends a check request to HA with its current ETag
3. HA fetches fresh calendar/weather data and renders the bitmap
4. If the render changed → ESP32 downloads new bitmaps and refreshes the display
5. If unchanged → HA returns 304, ESP32 skips the download (saves battery)
6. ESP32 goes back to deep sleep for the configured refresh interval

The refresh interval is propagated from HA to the ESP32 via HTTP headers, so changing it in the HA config takes effect on the next check-in.

## Display Layout

### Landscape (Recommended) — 1304×984

```
+---------------------------+--------------------------------------------------+
|                           |  LUN  |  MAR  |  MER  |  JEU  |  VEN  |  SAM  |
|  Today                    |  Weather icon + hi/lo temps                      |
|  Day name + date          |  Events for each day                             |
|  Weather + events         |                                                  |
|                           |--------------------------------------------------|
|  Calendar legend          |  Upcoming — events beyond the 6-day view         |
+---------------------------+--------------------------------------------------+
```

## Architecture

```
Home Assistant
  ├── Calendar entities (data source)
  ├── Weather entity (optional)
  └── E-Ink Calendar integration
        ├── Coordinator (fetches data on ESP32 check-in)
        ├── Renderer (generates bitmap from events + weather)
        ├── Announce API (device discovery, no auth)
        └── Bitmap API (serves layers, MAC-based auth)

ESP32
  ├── mDNS discovery → finds HA
  ├── Announce → registers with HA
  ├── Check → triggers render, gets ETag
  ├── Fetch → downloads changed bitmaps
  └── Display → renders on e-paper, deep sleeps
```

## API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/eink_calendar/announce` | None | Device discovery and status check |
| `GET /api/eink_calendar/bitmap/{entry_id}/{layer}` | X-MAC header | Bitmap serving |
| `GET /api/eink_calendar/bitmap/{entry_id}/check` | X-MAC header | ETag check (triggers re-render) |

## Troubleshooting

### Display shows "M1 Busy" and hangs
Ensure `DEV_ModuleInit()` is called before `EPD_12in48B_Init()` in the firmware.

### ESP32 can't find Home Assistant
- Ensure mDNS is working on your network (HA must be discoverable via `_home-assistant._tcp`)
- As a fallback, enter the HA URL manually in the WiFi setup portal
- Both devices must be on the same network/VLAN

### No events showing
- Ensure at least one calendar is selected in the integration options
- Check that the calendar entities have events in the displayed date range
- Check HA logs for "Calendar entities not ready" errors after restart (normal — HA retries automatically)

### Calendar shows wrong language
Change the **Language** setting in the device options (**Settings > Devices & Services > E-Ink Calendar > Configure**).

### Weather not showing
- Some weather integrations don't include today in their daily forecast — the integration falls back to current conditions automatically
- Verify the weather entity has data in **Developer Tools > States**

## Battery Life

With a 2000mAh battery and 15-minute refresh interval:
- Most check-ins result in 304 Not Modified (~5s active time)
- Full bitmap refresh only when calendar data changes (~15s active time)
- Expected battery life: weeks to months depending on how often events change

## Development

### Running Tests

```bash
cd custom_components/eink_calendar/tests
./run_tests.sh
```

64 unit tests covering event processing, filtering, weather utilities, rendering, and visual regression.

You can filter tests with pytest arguments:

```bash
./run_tests.sh -k "weather"        # Only weather tests
./run_tests.sh -k "process_events" # Only event processing tests
```

### Test Environment

```bash
docker-compose up  # Starts HA with the component mounted
```

### Project Structure

```
epcal/
├── Arduino/epcal/                  # ESP32 firmware (PlatformIO)
│   └── src/
│       ├── epcal.ino              # Main sketch (mDNS + announce + display)
│       ├── config.*               # NVS storage for HA URL, endpoints
│       ├── display.*              # E-paper display driver
│       └── http_client.*          # HTTP client (announce + ETag)
├── custom_components/eink_calendar/ # Home Assistant custom component
│   ├── renderer/                   # Python calendar renderer
│   │   ├── i18n.py                # French/English translations
│   │   ├── section_renderers/     # Today, week, upcoming panels
│   │   └── renderer.py           # Main render pipeline
│   ├── tests/                     # Unit and integration tests
│   ├── config_flow.py            # Discovery + manual config flow
│   ├── coordinator.py            # Data coordinator (on-demand refresh)
│   ├── http_views.py             # Announce + bitmap API
│   └── services.py               # trigger_render service
├── docs/                          # Technical documentation
└── docker-compose.yml             # HA test environment
```

## Contributing

Issues and pull requests welcome at https://github.com/emilecantin/ha-eink-calendar

## License

MIT

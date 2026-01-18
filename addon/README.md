# EPCAL - E-Paper Calendar Add-on

Render your Home Assistant calendars to an e-paper display.

## Features

- Displays events from multiple Home Assistant calendars
- Weather forecast integration
- Portrait and landscape layouts
- Automatic refresh with ETag caching (saves device battery)
- French UI (English coming soon)

## Installation

1. Add this repository to Home Assistant:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the menu (⋮) → **Repositories**
   - Add: `https://gitlab.com/emilecantin/epcal`

2. Find "EPCAL - E-Paper Calendar" in the add-on store and click **Install**

3. Start the add-on and open the Web UI

## Configuration

The add-on automatically connects to Home Assistant - no manual token configuration needed.

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `log_level` | Logging verbosity (debug, info, warning, error) | `info` |

### Web UI Settings

- **Calendars**: Select which calendars to display and customize their icons/names
- **Layout**: Choose portrait or landscape orientation
- **Weather**: Select a weather entity for forecast display
- **Legend**: Toggle the calendar legend on/off

## Hardware

This add-on renders calendar images for e-paper displays. You'll need:

- **ESP32 board** with WiFi (e.g., ESP32 DevKit, Waveshare E-Paper Driver Board)
- **E-paper display** (currently optimized for Waveshare 12.48" tri-color)

The ESP32 firmware is available in the `Arduino/` directory of this repository.

## API Endpoints

The add-on exposes these endpoints for the ESP32:

| Endpoint | Description |
|----------|-------------|
| `/calendar/check` | ETag check (returns 304 if unchanged) |
| `/calendar/black1` | Black layer, top half |
| `/calendar/black2` | Black layer, bottom half |
| `/calendar/red1` | Red layer, top half |
| `/calendar/red2` | Red layer, bottom half |
| `/calendar/preview` | Full PNG preview |

## Support

- [GitHub Issues](https://gitlab.com/emilecantin/epcal/issues)
- [Documentation](https://gitlab.com/emilecantin/epcal)

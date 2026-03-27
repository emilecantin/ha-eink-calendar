# E-Ink Calendar — Home Assistant Integration

Native Home Assistant integration for rendering calendars to e-paper displays.

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=emilecantin&repository=ha-eink-calendar&category=integration)

### Manual

1. Copy this `eink_calendar` directory to `config/custom_components/eink_calendar/`
2. Restart Home Assistant
3. Go to **Settings > Devices & Services > Add Integration**
4. Search for "E-Ink Calendar"

## Configuration

All settings are configured through the HA UI. Each device can be configured independently.

| Option | Description | Default |
|--------|-------------|---------|
| Calendars | Calendar entities to display with full event details | — |
| Waste Calendars | Calendar entities shown as icons only | — |
| Language | Display language (Français / English) | French |
| Layout | Landscape (recommended) or Portrait | Landscape |
| Show Legend | Calendar icon legend at bottom of display | On |
| Weather Entity | Weather entity for daily forecast | — |
| Refresh Interval | How often ESP32 checks for updates (minutes) | 15 |
| Custom Fonts | Optional paths to TTF fonts (Regular, Medium, Bold) | Bundled Inter |

After initial setup, change options via **Settings > Devices & Services > E-Ink Calendar > Configure**.

### Waste Calendar Icons

When waste calendars are configured, a second configuration step lets you assign MDI icons to each waste type (detected from event summaries). These icons appear in the day columns on collection days.

## Entities

Each device creates:

- `camera.{name}_preview` — Full-color PNG preview
- `image.{name}_black_layer_{top,bottom}` — Black bitmap layers for ESP32
- `image.{name}_red_layer_{top,bottom}` — Red bitmap layers for ESP32
- `sensor.{name}_last_update` — Last render timestamp
- `sensor.{name}_last_checkin` — Last ESP32 check-in timestamp

## Services

| Service | Description |
|---------|-------------|
| `eink_calendar.trigger_render` | Force a fresh render (clears cache, re-fetches data) |

## How It Works

1. **No polling** — The integration does not poll on a schedule
2. **ESP32 triggers renders** — When the ESP32 checks in (`/check` endpoint), the integration fetches fresh calendar and weather data and renders the bitmap
3. **ETag caching** — If the render hasn't changed, the ESP32 gets a 304 and skips the download
4. **Pre-rendered cache** — Bitmaps are cached after render so the camera preview and image entities serve instantly

## Troubleshooting

### Integration fails to load after restart
Calendar or weather entities may not be ready yet. The integration raises `ConfigEntryNotReady` and HA retries automatically — check logs for "will retry" messages.

### Preview shows but ESP32 doesn't update
- Verify the ESP32 is checking in (watch `sensor.{name}_last_checkin`)
- Check that the MAC address matches between the config entry and the ESP32's `X-MAC` header
- Check HA logs for bitmap endpoint errors

### Wrong language on display
Change the **Language** option in device settings.

### Weather not showing
- Some weather integrations don't include today in daily forecasts — the integration falls back to current conditions
- Verify the weather entity has data in **Developer Tools > States**

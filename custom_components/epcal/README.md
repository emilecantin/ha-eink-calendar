# EPCAL - E-Paper Calendar Integration

Native Home Assistant integration for rendering calendars to e-paper displays.

## Installation

### Manual Installation

1. Copy the `custom_components/epcal` directory to your Home Assistant `config/custom_components/` directory:

```bash
cd /path/to/your/homeassistant/config
mkdir -p custom_components
cp -r /Users/emilecantin/Documents/Projets/iot/epcal/custom_components/epcal custom_components/
```

2. Restart Home Assistant

3. Go to **Settings → Devices & Services**

4. Click **+ Add Integration**

5. Search for "E-Paper Calendar" and click it

6. Follow the setup wizard:
   - Enter a device name (e.g., "Kitchen Calendar")
   - Click Submit

7. Configure options:
   - Select regular calendars to display
   - Select waste collection calendars (if using Waste Collection Schedule integration)
   - Choose layout (landscape recommended)
   - Optionally select a weather entity
   - Optionally specify custom font paths

## Features (MVP Version)

This is a minimal viable product for initial testing. Current features:

✅ Multi-device support (multiple e-paper displays)
✅ Calendar event fetching from HA calendars
✅ Waste collection calendar support
✅ Weather integration (optional)
✅ Camera entity (preview)
✅ Image entities (4 bitmap layers for ESP32)
✅ ETag caching (via HA image proxy)
✅ Custom font support
✅ Configurable via UI

🚧 **Coming Soon** (to match TypeScript server):
- Full section renderers (Today, Week, Upcoming)
- Event rendering with icons and times
- Weather forecast display
- Legend display
- Collection icons in corners
- Portrait layout support

## Entities Created

Each EPCAL device creates:

- `camera.{device_name}_preview` - Full-color PNG preview
- `image.{device_name}_black_layer_top` - Top half black bitmap
- `image.{device_name}_black_layer_bottom` - Bottom half black bitmap
- `image.{device_name}_red_layer_top` - Top half red bitmap
- `image.{device_name}_red_layer_bottom` - Bottom half red bitmap
- `sensor.{device_name}_last_update` - Last render timestamp

## ESP32 Integration

### Image URLs

ESP32 devices fetch images via HA's image proxy:

```cpp
// Check ETag
HEAD http://homeassistant.local:8123/api/image_proxy/image.kitchen_calendar_black_layer_top
Authorization: Bearer YOUR_LONG_LIVED_TOKEN

// Fetch images (if ETag changed)
GET http://homeassistant.local:8123/api/image_proxy/image.kitchen_calendar_black_layer_top
GET http://homeassistant.local:8123/api/image_proxy/image.kitchen_calendar_black_layer_bottom
GET http://homeassistant.local:8123/api/image_proxy/image.kitchen_calendar_red_layer_top
GET http://homeassistant.local:8123/api/image_proxy/image.kitchen_calendar_red_layer_bottom
```

HA automatically handles ETag caching and returns `304 Not Modified` when unchanged.

## Testing the Integration

1. **Check entities are created:**
   - Go to **Developer Tools → States**
   - Search for your device name
   - Verify camera, image, and sensor entities exist

2. **View the preview:**
   - Go to **Settings → Devices & Services → EPCAL**
   - Click on your device
   - Click on the camera entity
   - You should see a preview image

3. **Test image endpoints:**
   - Get a long-lived access token: **Profile → Long-Lived Access Tokens**
   - Test in browser:
     ```
     http://homeassistant.local:8123/api/image_proxy/image.{device_name}_black_layer_top?token=YOUR_TOKEN
     ```
   - Should download binary data

4. **Check logs:**
   ```bash
   # In Home Assistant container or logs
   grep -i epcal home-assistant.log
   ```

## Configuration Options

### Regular Calendars
Select which HA calendar entities to display with full event details (time, title, icon).

### Waste Collection Calendars
Select calendar entities that should display only icons (no event text). Works with [Waste Collection Schedule](https://github.com/mampfes/hacs_waste_collection_schedule) integration.

### Layout
- **Landscape** (recommended): 1304×984 - Today on left, week + upcoming on right
- **Portrait**: 984×1304 - Not implemented in MVP

### Weather Entity
Optional weather entity for forecast display.

### Custom Fonts
Optional paths to custom TTF fonts (Regular, Medium, Bold). Leave blank to use bundled Inter fonts.

Example:
```
/config/fonts/MyFont-Regular.ttf
/config/fonts/MyFont-Medium.ttf
/config/fonts/MyFont-Bold.ttf
```

## Troubleshooting

### Integration doesn't load
- Check Home Assistant logs for errors
- Ensure Pillow is installed: `pip list | grep -i pillow`
- Restart Home Assistant completely

### No preview image
- Check that calendars are selected in options
- Check Developer Tools → States for camera entity state
- Look for errors in logs

### ESP32 can't fetch images
- Verify long-lived access token is correct
- Check ESP32 can reach HA (ping test)
- Test image URL in browser first
- Check HA logs for authentication errors

### Fonts not loading
- Check font file paths are absolute (e.g., `/config/fonts/...`)
- Verify font files exist and are readable
- Integration will fall back to bundled Inter fonts on error

## Development Status

**Current Version: 0.1.0 (MVP)**

This is an initial minimal viable product for testing the integration architecture. The rendering currently shows placeholder content.

**Next Steps:**
1. Port full section renderers from TypeScript
2. Implement complete event rendering
3. Add weather forecast display
4. Add legend rendering
5. Add portrait layout support

## Support

- Issues: https://gitlab.com/emilecantin/epcal/-/issues
- Documentation: https://gitlab.com/emilecantin/epcal

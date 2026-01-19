# EPCAL Roadmap

## Current State (January 2025)

Working e-paper calendar display system:
- **Server**: Node.js/Express with Canvas-based rendering
- **Firmware**: ESP32 with Waveshare 12.48" tri-color e-paper (1304x984, black/white/red)
- **Features**: Home Assistant calendar integration, weather forecast, configurable layout (portrait/landscape), calendar legend, French UI

## Phase 1: Home Assistant Add-on (Done)

Convert the existing server into a Home Assistant Add-on for easier distribution.

### Implementation
- **Add-on files**: `addon/` directory with config.yaml, Dockerfile, run.sh
- **CI/CD**: GitLab CI builds multi-arch images (amd64, arm64, armv7)
- **Registry**: Images pushed to `registry.gitlab.com/emilecantin/epcal/addon`
- **Server changes**: Supports `ADDON_MODE` with auto-configured HA connection

### Add-on Structure
```
addon/
├── config.yaml          # Add-on metadata, references pre-built image
├── Dockerfile           # Multi-arch build with bashio for Supervisor API
├── build.yaml           # Build configuration for different architectures
├── run.sh               # Startup script (reads Supervisor env vars)
└── README.md            # Installation instructions
```

### Features Implemented
- [x] Read HA URL/token from Supervisor API (auto-discovery)
- [x] Ingress support for seamless UI integration
- [x] Options schema for configuration via HA UI
- [x] Multi-arch builds via GitLab CI (amd64, arm64, armv7)
- [x] Separate weather config UI for add-on mode

### How to Install (HA OS/Supervised)
1. Add repository: `https://gitlab.com/emilecantin/epcal`
2. Install "EPCAL - E-Paper Calendar" from add-on store
3. Start add-on and open Web UI via Ingress

### Limitations
- Only works with HA OS / Supervised installs
- Docker HA users can run the standalone server instead

---

## Phase 2: Native Home Assistant Integration (Future)

Full Python integration that runs inside Home Assistant, distributable via HACS.

### Why Native Integration
- Works on ALL HA installs (Docker, Core, OS, Supervised)
- Deeper integration (entities, services, automations)
- Camera entity for easy Lovelace preview
- HACS distribution reaches more users

### Architecture

```
custom_components/epcal/
├── manifest.json        # Integration metadata, dependencies (Pillow)
├── __init__.py          # async_setup_entry() - integration setup
├── config_flow.py       # UI-based configuration wizard
├── camera.py            # Camera entity serving rendered image
├── coordinator.py       # DataUpdateCoordinator for calendar fetching/caching
├── renderer.py          # Pillow-based rendering (port from renderer.ts)
├── const.py             # Constants (domain name, default values)
└── strings.json         # Translations
```

### Key Components to Port

#### Renderer (renderer.ts → renderer.py)
The main work - port Canvas rendering to Pillow:
- Text rendering with custom fonts (Inter)
- Layout calculations (today section, week grid, upcoming)
- Color handling (black layer, red layer for tri-color)
- Weather icons (Unicode symbols)
- Legend rendering
- Bitmap conversion for e-paper (1-bit, MSB first)

Pillow equivalents:
- `ctx.fillText()` → `ImageDraw.text()`
- `ctx.fillRect()` → `ImageDraw.rectangle()`
- `ctx.measureText()` → `font.getbbox()` or `font.getlength()`
- Custom fonts via `ImageFont.truetype()`

#### Calendar Data Fetching
- Use HA's `calendar.get_events` service instead of REST API
- Access weather entities directly via `hass.states`
- DataUpdateCoordinator pattern for caching/refresh

#### Camera Entity
```python
class EpcalCamera(Camera):
    """Camera entity that serves the rendered calendar image."""

    async def async_camera_image(self):
        """Return the rendered calendar as PNG."""
        return self.coordinator.rendered_png
```

Benefits:
- Preview in Lovelace: `type: picture-entity`
- Use in automations
- HA handles image caching/proxy

#### Config Flow
UI-based setup wizard:
1. Select calendars to display
2. Choose layout (portrait/landscape)
3. Select weather entity (optional)
4. Configure display settings

### ESP32 Integration Options

Once server is an HA integration, ESP32 can:
1. **Keep current approach**: Fetch from HA's camera entity URL
2. **ESPHome integration**: Native ESPHome component (more complex)
3. **HA webhook**: ESP32 calls webhook, HA pushes image (saves polling)

### Learning Resources
- HA Developer Docs: https://developers.home-assistant.io/
- Integration examples: `hacs/integration` repos on GitHub
- Similar projects: `google_photos`, `generic_camera` integrations
- Pillow docs: https://pillow.readthedocs.io/

---

## Phase 3: Multi-Display Support (Future)

Support different e-paper displays beyond Waveshare 12.48".

### Display Profile System
```typescript
interface DisplayProfile {
  id: string;                    // "waveshare_12_48_bwr"
  name: string;                  // "Waveshare 12.48\" B/W/R"
  width: number;                 // 1304
  height: number;                // 984
  colors: "bw" | "bwr" | "bwy" | "grayscale";
  rotation: 0 | 90 | 180 | 270;
  chunkSize?: number;            // For memory-constrained ESP32
  refreshTime?: number;          // Typical full refresh time in seconds
}
```

### Potential Displays to Support
- Waveshare 7.5" (800x480) - popular smaller option
- Waveshare 4.2" (400x300) - compact
- Good Display e-papers
- Grayscale displays (more shades, no red)

### Renderer Changes Needed
- Resolution-independent layout calculations
- Aspect ratio handling (different layouts for portrait vs landscape)
- Color mode adaptation (skip red layer for B/W displays)
- Font size scaling based on DPI/resolution

### Firmware Changes
- Display driver abstraction layer
- Runtime display selection or compile-time config
- Adjust chunk sizes per display memory requirements

---

## Hardware / Battery Testing (Pending)

### Deep Sleep Current Measurement
- [ ] Measure actual deep sleep current with 18650 battery
- [ ] Identify any power-hungry components (USB-UART chip, regulator)
- [ ] Calculate expected battery life based on measurements

### Battery Setup
- **Board**: Waveshare E-Paper ESP32 Driver Board (3.6-5.5V input)
- **Cells**: 18650 Li-ion (waiting for battery holders to arrive)
- **Considerations**:
  - May need over-discharge protection (don't go below 2.5-3.0V)
  - Consider adding battery voltage monitoring via ADC

### Power Optimization (if needed)
- [ ] Tune refresh interval based on battery life requirements
- [ ] Investigate disabling USB-UART chip during sleep
- [ ] Consider brownout detection settings for low battery

---

## Other Improvements (Backlog)

### Documentation
- [ ] Comprehensive README with screenshots
- [ ] Hardware shopping list with links
- [ ] Step-by-step assembly guide
- [ ] Video tutorial?

### Internationalization
- [ ] Extract French strings to i18n system
- [ ] Add English translation
- [ ] Make language configurable

### Configuration
- [ ] Environment variable support (for Docker deployments)
- [ ] Configuration validation with helpful errors
- [ ] Import/export config

### Distribution
- [ ] GitHub releases with changelog
- [ ] Docker Hub published image
- [ ] Home Assistant Add-on repository
- [ ] HACS default repository submission (once stable)

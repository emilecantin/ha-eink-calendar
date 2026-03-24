# EPCAL Project Structure

## Overview

```
epcal/
├── scripts/                    # Developer utility scripts
├── server/                     # Node.js rendering server
├── Arduino/                    # ESP32 firmware
├── custom_components/          # Home Assistant integration
├── tests/                      # Python test suite
├── docs/                       # Documentation
├── comparison_tests/           # Visual regression test results
├── ha-test-config/            # Home Assistant test environment
└── docs/                       # Documentation
```

## Directory Details

### `/scripts/` - Development Scripts

Utility scripts for testing and analysis.

- `analyze_diffs.py` - Advanced pixel difference analyzer (requires NumPy)
- `analyze_diffs_simple.py` - Lightweight version (PIL only)
- `run_tests.py` - Main test runner for complete suite

See [scripts/README.md](scripts/README.md) for usage.

### `/server/` - Rendering Server

Node.js/TypeScript server that renders calendar bitmaps for the e-paper display.

**Core files**:
- `index.ts` - Main server, HTTP endpoints, config UI
- `renderer.ts` - Canvas-based bitmap rendering
- `event-renderer.ts` - Calendar event layout
- `weather-utils.ts` - Weather data formatting

**Subdirectories**:
- `section-renderers/` - Modular section rendering (today, upcoming, week, indicators)
- `scripts/` - Server utility scripts (icon downloads)
- `fonts/` - Inter font files for e-paper
- `__tests__/` - Jest test suite
- `dist/` - Compiled JavaScript output

### `/Arduino/epcal/` - ESP32 Firmware

PlatformIO project for the ESP32 microcontroller.

**Key files**:
- `src/epcal.ino` - Main sketch with state machine
- `src/config.*` - NVS storage for WiFi/server config
- `src/display.*` - E-paper display driver
- `generate_qr.js` - Generates setup screen with QR codes

### `/custom_components/epcal/` - Home Assistant Integration

Python custom component that integrates EPCAL as a Home Assistant service.

**Structure**:
- `renderer/` - Pure Python renderer (matches TypeScript output)
- `tests/` - Integration and unit tests
- `__init__.py` - HA integration setup
- `config_flow.py` - Configuration UI

### `/tests/` - Test Suite

Python tests for the renderer and integration.

**Structure**:
- `fixtures/` - Shared test data
  - `test_data_library.py` - Test scenario definitions
  - `test_scenarios.json` - JSON scenarios for TS/Python comparison
- `utils/` - Test generation and analysis tools
- `debug/` - One-off debugging scripts

See [tests/README.md](tests/README.md) for details.

### `/docs/` - Documentation

Technical documentation and guides.

- `TESTING.md` - Visual regression testing guide
- `BORDER_FIX_RESULTS.md` - Border alignment technical details
- `screenshots/` - UI screenshots
- `archive/` - Historical documentation

### `/comparison_tests/` - Test Results

Generated output from visual regression tests comparing TypeScript and Python renderers.

Contains:
- `*_typescript.png` - TypeScript renderer output
- `*_python.png` - Python renderer output
- `*_diff.png` - Pixel difference visualization
- `comparison_report.html` - Interactive comparison report

### `/ha-test-config/` - Test Environment

Home Assistant configuration for testing the integration.

**Note**: `test_data_library.py` is a symlink to `tests/fixtures/test_data_library.py`

## Root Files

- `CLAUDE.md` - Development guidelines for Claude Code
- `README.md` - Main project documentation
- `docker-compose.yml` - Home Assistant test environment
- `pyrightconfig.json` - Python type checking configuration

## Build Artifacts (gitignored)

- `server/dist/` - Compiled TypeScript
- `server/node_modules/` - NPM dependencies
- `**/__pycache__/` - Python bytecode
- `coverage/` - Test coverage reports

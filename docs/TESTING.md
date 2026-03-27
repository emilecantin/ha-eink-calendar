# Testing

## Unit Tests

The renderer unit tests are in `custom_components/eink_calendar/tests/`.

### Running Tests

```bash
cd custom_components/eink_calendar/tests
./run_tests.sh
```

The script automatically creates a Python venv (if needed) with pytest, Pillow, and python-dateutil.

### Filtering Tests

Pass any pytest arguments through the script:

```bash
./run_tests.sh -k "weather"            # Only weather tests
./run_tests.sh -k "process_events"     # Only event processing
./run_tests.sh -k "collection_icons"   # Only collection icon tests
./run_tests.sh --no-header -q          # Quiet output
```

### Test Files

| File | What it tests |
|------|---------------|
| `test_process_events.py` | Date parsing, all-day end date adjustment, calendar field passthrough, naive/aware mixing |
| `test_event_filters.py` | `get_events_for_day` (single/multi-day, boundaries, exclusion), `get_collection_icons_for_day` |
| `test_event_renderer.py` | `format_multi_day_time` (arrows), `sort_events_by_priority` (all-day first) |
| `test_weather_utils.py` | `get_forecast_for_date` (matching, missing data, timezone handling) |
| `test_renderer_integration.py` | Full `render_calendar` + `render_to_png` pipeline, legend creation |
| `test_firmware_sensor.py` | Firmware version sensor entity (value from coordinator, listener registration) |
| `test_visual_regression.py` | Renders various scenarios to PNG for visual inspection |

### Visual Regression

The visual regression tests in `test_visual_regression.py` render 12 different scenarios to PNG files in `tests/visual_output/` and generate an HTML report. These are useful for checking rendering changes visually:

```bash
./run_tests.sh test_visual_regression.py -s  # -s shows print output with file paths
open visual_output/visual_regression_report.html
```

### How Tests Work

Tests import renderer modules directly (not through the HA integration). The `conftest.py` adds the `eink_calendar/` directory to `sys.path` so imports like `from renderer.event_filters import ...` work without needing Home Assistant installed.

## Integration Testing

Start a local HA instance with the component mounted:

```bash
docker-compose up
```

Then test the device flow:

```bash
# Test announce (simulates ESP32 first contact)
curl -X POST http://localhost:8123/api/eink_calendar/announce \
  -H "Content-Type: application/json" \
  -d '{"mac":"AA:BB:CC:DD:EE:FF","name":"Test Calendar","firmware_version":"1.0.0"}'

# After configuring the device in HA UI:
# Test bitmap check
curl http://localhost:8123/api/eink_calendar/bitmap/{entry_id}/check \
  -H "X-MAC: AA:BB:CC:DD:EE:FF"

# Test bitmap download
curl http://localhost:8123/api/eink_calendar/bitmap/{entry_id}/black_top \
  -H "X-MAC: AA:BB:CC:DD:EE:FF" -o black_top.bin
```

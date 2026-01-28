# EPCAL Visual Regression Testing

## Quick Start

Run all tests with a single command:

```bash
python3 scripts/run_tests.py
```

This will:
1. Generate TypeScript reference renders (12 scenarios)
2. Generate Python renders using standalone renderer (12 scenarios)
3. Analyze pixel differences
4. Generate HTML comparison report

View results: `open comparison_tests/comparison_report.html`

## Test Files

### Main Entry Point
- **`scripts/run_tests.py`** - Single command to run complete test suite

### Core Files
- **`tests/fixtures/test_data_library.py`** - Shared test scenarios used by both renderers
- **`tests/fixtures/test_scenarios.json`** - JSON test scenarios for TypeScript/Python comparison
- **`epcal_renderer/`** - Standalone Python renderer package (no HA dependencies)
- **`test_with_standalone_renderer.py`** - Quick test of single scenario
- **`regenerate_all_tests.py`** - Generate all Python test renders
- **`analyze_differences.py`** - Compute pixel-level differences
- **`create_comparison_report.py`** - Generate HTML side-by-side comparison

### TypeScript Renderer
- **`server/generate_test_renders.ts`** - Generate TypeScript reference renders
- **`test_data_library.js`** - TypeScript version of test scenarios

## Test Scenarios

12 test scenarios covering different calendar features:

1. **empty_calendar** - No events, no weather
2. **single_event_tomorrow** - One event tomorrow
3. **multiple_events_tomorrow** - Multiple events tomorrow
4. **all_day_events** - All-day events with triangles
5. **multi_day_event** - Event spanning multiple days
6. **long_title_wrapping** - Long event titles that wrap
7. **overflow_events** - More events than fit (overflow indicator)
8. **weekend_event** - Weekend day with red background
9. **waste_collection** - Waste collection icons
10. **weather_forecast** - Weather data display
11. **upcoming_events** - Events in upcoming section
12. **full_calendar** - All features combined

## Expected Results

After running tests, you should see:

- **1.7-2.6% pixel difference** - Normal (font rendering differences between Canvas and PIL)
- **~5% for waste_collection** - Under investigation
- **Borders match exactly** - x=15-16, y=15-16 for both renderers

## Border Alignment Fix

The Python renderer now matches TypeScript border alignment:

- **Issue**: PIL draws borders INSIDE coordinates, Canvas draws CENTERED
- **Fix**: Offset all border drawing by -1 pixel
- **Result**: Pixel-perfect border alignment

See `BORDER_FIX_RESULTS.md` for details.

## Standalone Renderer

The `epcal_renderer/` package can be used independently without Home Assistant:

```python
from epcal_renderer import render_to_png

png_data = render_to_png(
    calendar_events,
    waste_events,
    weather_data,
    current_time,
    options
)
```

This allows:
- Local testing without Docker
- Use in other projects
- Easier development and debugging

## Development Workflow

### Making Changes

1. Edit renderer code in `epcal_renderer/`
2. Run tests: `./run_tests.py`
3. Review differences in HTML report
4. Sync changes to HA integration:
   ```bash
   cp epcal_renderer/section_renderers/*.py custom_components/epcal/section_renderers/
   # Fix imports for HA
   cd custom_components/epcal/section_renderers
   sed -i '' 's/from \.\.const import/from ...const import/g' landscape_*.py
   sed -i '' 's/from \.\.event_filters import/from ..renderer.event_filters import/g' landscape_*.py
   ```

### Quick Single Test

Test one scenario without regenerating everything:

```bash
python3 test_with_standalone_renderer.py
```

This tests `single_event_tomorrow` and verifies border alignment.

## Output

All generated files go to `comparison_tests/`:

- `*_typescript.png` - Reference renders from TypeScript
- `*_python.png` - Renders from Python standalone renderer
- `*_comparison.png` - Side-by-side comparison images
- `*_diff.png` - Difference visualization (if generated)
- `comparison_report.html` - Interactive HTML report

## Troubleshooting

### Font warnings
```
Failed to load bundled font: cannot open resource
Using system default font
```
This is expected when running standalone renderer - it falls back to system fonts. Visual output is still correct for testing borders and layout.

### TypeScript build fails
```bash
cd server && npm install
```

### Python imports fail
Ensure you're running from the project root directory where `epcal_renderer/` exists.

# EPCAL Visual Regression Test Results

## Summary

All 11 visual regression tests passed successfully, generating renders from the Python implementation for comparison with the TypeScript reference.

## Test Results

| Test | Description | Status | Size |
|------|-------------|--------|------|
| 01 | Full Calendar | ✓ | 50 KB |
| 02 | Today Section | ✓ | 39 KB |
| 03 | Week - All-Day Events | ✓ | 26 KB |
| 04 | Week - Multi-Day Event | ✓ | 28 KB |
| 05 | Weekend Highlighting | ✓ | 26 KB |
| 06 | Waste Collection Icons | ✓ | 24 KB |
| 07 | Weather Display | ✓ | 28 KB |
| 08 | Text Wrapping | ✓ | 27 KB |
| 09 | Overflow Indicator | ✓ | 42 KB |
| 10 | Empty Calendar | ✓ | 21 KB |
| 11 | Upcoming Section | ✓ | 31 KB |

## Bug Fixed

During test execution, discovered and fixed a function signature error:
- **File**: `landscape_upcoming.py:124`
- **Issue**: `truncate_text()` was called with incorrect parameters (included `draw` as first param)
- **Fix**: Removed `draw` parameter to match function signature `truncate_text(text, max_width, font)`

## Review Instructions

1. **Open the HTML Report**: `visual_regression_report.html`
   - Contains all 11 test renders in a convenient browser view
   - Includes file sizes and test descriptions

2. **Compare with TypeScript Reference**
   - Look for visual differences in rendering between Python and TypeScript implementations
   - Focus on these areas:
     - Font rendering and spacing
     - Text alignment and positioning
     - Icon placement and size
     - Line widths and colors
     - Section boundaries and spacing
     - Multi-day event indicators (arrows, triangles)
     - Weather icons and temperature formatting
     - Waste collection icon positioning
     - Overflow indicators (+X more)
     - Weekend highlighting (red background)

3. **Test Scenarios Covered**
   - **Test 1**: Complete calendar with events, weather, and waste collection
   - **Test 2**: Today section with various event types (timed, all-day, multi-day)
   - **Test 3**: Week view with all-day events
   - **Test 4**: Week view with multi-day event spanning 3 days
   - **Test 5**: Weekend highlighting (Saturday event with red background)
   - **Test 6**: Waste collection icons in calendar grid
   - **Test 7**: Weather forecast display with icons and temperatures
   - **Test 8**: Long event titles with text wrapping
   - **Test 9**: Overflow handling with 15 events ("+X more" indicator)
   - **Test 10**: Empty calendar (no events)
   - **Test 11**: Upcoming events section (events beyond 6-day view)

## Running Tests

The test suite can be re-run at any time:

```bash
# Copy test script to container
docker cp test_visual_regression_suite.py ha-epcal-test:/config/

# Run tests
docker exec ha-epcal-test python3 /config/test_visual_regression_suite.py

# Copy results back
docker cp ha-epcal-test:/config/visual_test_output ./
```

## Test Data

All tests use a consistent reference date: **Sunday, January 25, 2026 at 8:00 PM**

This ensures predictable rendering across:
- Today section (Sunday)
- Week section (Monday-Saturday)
- Upcoming section (events beyond Saturday)
- Weekend highlighting (Saturday/Sunday)

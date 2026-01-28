# Test Fixtures

Shared test data used across the test suite.

## Files

### `test_data_library.py`
Python module containing test scenario definitions used by the renderer tests.

**Contains**:
- Sample calendar events
- Weather data structures
- Waste collection events
- Reusable test data functions

**Used by**:
- Python renderer tests
- Home Assistant test configuration
- Visual regression tests

**Note**: A symlink to this file exists in `ha-test-config/` for compatibility with the Home Assistant test environment.

### `test_scenarios.json`
JSON file containing shared test scenarios for TypeScript/Python renderer comparison.

**Structure**:
```json
{
  "NOW": "2026-01-26T08:00:00",
  "scenarios": {
    "empty_calendar": { ... },
    "single_event_tomorrow": { ... },
    ...
  }
}
```

**Used by**:
- `tests/utils/regenerate_all_tests.py` - Python test render generator
- Server TypeScript test render generator
- Visual regression comparison tests

## Usage

These fixtures ensure both TypeScript and Python renderers are tested with identical data, making visual comparison tests meaningful.

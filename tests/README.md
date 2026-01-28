# EPCAL Test Suite

This directory contains the test infrastructure for the EPCAL renderer.

## Directory Structure

```
tests/
├── utils/                          # Test utilities and generators
│   ├── regenerate_all_tests.py    # Generate Python test renders
│   ├── analyze_differences.py     # Compute pixel differences
│   └── create_comparison_report.py # Generate HTML comparison report
├── debug/                          # Debug scripts for troubleshooting
│   ├── check_*.py                 # Border alignment checkers
│   ├── debug_*.py                 # Pixel-level debugging tools
│   └── test_*.py                  # PIL rendering behavior tests
└── test_with_standalone_renderer.py # Standalone renderer integration test
```

## Running Tests

From the project root:

```bash
# Run full test suite (TypeScript + Python + comparison)
python3 scripts/run_tests.py

# Just regenerate Python renders
python3 tests/utils/regenerate_all_tests.py

# Just create comparison report
python3 tests/utils/create_comparison_report.py
```

## Test Data

- `fixtures/test_data_library.py` - Test scenario definitions
- `fixtures/test_scenarios.json` - Shared test scenarios for TypeScript/Python comparison
- `comparison_tests/` - Generated test outputs and comparison images (in project root)

## Debug Scripts

The `debug/` directory contains one-off scripts used during development to troubleshoot
specific rendering issues. These are kept for reference but not part of the regular
test suite.

# Developer Scripts

Utility scripts for development, testing, and analysis.

## Analysis Scripts

### `analyze_diffs.py`
Full-featured rendering difference analyzer using NumPy.

**Requirements**: `numpy`, `Pillow`

**Features**:
- Advanced pixel analysis with bounding boxes
- RGB channel difference detection
- Antialiasing vs solid color pattern detection
- Statistical analysis of differences

**Usage**:
```bash
python scripts/analyze_diffs.py
```

Analyzes all `*_diff.png` files in `comparison_tests/` directory.

### `analyze_diffs_simple.py`
Lightweight rendering difference analyzer without NumPy dependency.

**Requirements**: `Pillow` only

**Features**:
- Simple pixel-by-pixel comparison
- Difference counting and sampling
- Works in environments without NumPy

**Usage**:
```bash
python scripts/analyze_diffs_simple.py
```

Use this version if NumPy is not available in your environment.

## Test Scripts

### `run_tests.py`
Main test runner for the EPCAL project.

**Usage**:
```bash
python scripts/run_tests.py
```

Runs the full test suite for the custom component.

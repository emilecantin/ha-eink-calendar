#!/usr/bin/env python3
"""Compare all border positions between TypeScript and Python renders."""

from PIL import Image

# Load both images
ts_img = Image.open("comparison_tests/empty_calendar_typescript.png")
py_img = Image.open("comparison_tests/empty_calendar_python.png")
ts_pixels = ts_img.load()
py_pixels = py_img.load()


def get_rgb(pixel):
    """Extract RGB from pixel (handles both RGB and RGBA)."""
    if len(pixel) == 4:
        return pixel[:3]
    return pixel


print("Border Position Comparison")
print("=" * 80)

# Check vertical border between Today and Week sections (x=399-400)
print("\n1. Vertical border between Today and Week (should be x=399-400):")
for x in [398, 399, 400, 401]:
    ts_black_count = 0
    py_black_count = 0
    for y in range(16, 968):
        if get_rgb(ts_pixels[x, y]) == (0, 0, 0):
            ts_black_count += 1
        if get_rgb(py_pixels[x, y]) == (0, 0, 0):
            py_black_count += 1
    print(
        f"  x={x}: TS has {ts_black_count} black pixels, Python has {py_black_count} black pixels"
    )

# Check top border (y=15-16)
print("\n2. Top border (should be y=15-16):")
for y in [14, 15, 16, 17]:
    ts_black_count = sum(
        1 for x in range(16, 1288) if get_rgb(ts_pixels[x, y]) == (0, 0, 0)
    )
    py_black_count = sum(
        1 for x in range(16, 1288) if get_rgb(py_pixels[x, y]) == (0, 0, 0)
    )
    print(
        f"  y={y}: TS has {ts_black_count} black pixels, Python has {py_black_count} black pixels"
    )

# Check bottom border (y=967-968)
print("\n3. Bottom border (should be y=967-968):")
for y in [966, 967, 968, 969]:
    ts_black_count = sum(
        1 for x in range(16, 1288) if get_rgb(ts_pixels[x, y]) == (0, 0, 0)
    )
    py_black_count = sum(
        1 for x in range(16, 1288) if get_rgb(py_pixels[x, y]) == (0, 0, 0)
    )
    print(
        f"  y={y}: TS has {ts_black_count} black pixels, Python has {py_black_count} black pixels"
    )

# Check left edge (x=15-16)
print("\n4. Left border (should be x=15-16):")
for x in [14, 15, 16, 17]:
    ts_black_count = sum(
        1 for y in range(16, 968) if get_rgb(ts_pixels[x, y]) == (0, 0, 0)
    )
    py_black_count = sum(
        1 for y in range(16, 968) if get_rgb(py_pixels[x, y]) == (0, 0, 0)
    )
    print(
        f"  x={x}: TS has {ts_black_count} black pixels, Python has {py_black_count} black pixels"
    )

# Check right edge (x=1287-1288)
print("\n5. Right border (should be x=1287-1288):")
for x in [1286, 1287, 1288, 1289]:
    ts_black_count = sum(
        1 for y in range(16, 968) if get_rgb(ts_pixels[x, y]) == (0, 0, 0)
    )
    py_black_count = sum(
        1 for y in range(16, 968) if get_rgb(py_pixels[x, y]) == (0, 0, 0)
    )
    print(
        f"  x={x}: TS has {ts_black_count} black pixels, Python has {py_black_count} black pixels"
    )

print("\n" + "=" * 80)

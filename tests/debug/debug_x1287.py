#!/usr/bin/env python3
"""Debug x=1287 vertical border (right edge)."""

from PIL import Image

# Load both images
ts_img = Image.open("comparison_tests/empty_calendar_typescript.png")
py_img = Image.open("comparison_tests/empty_calendar_python.png")
ts_pixels = ts_img.load()
py_pixels = py_img.load()


def get_rgb(pixel):
    if len(pixel) == 4:
        return pixel[:3]
    return pixel


print("Checking x=1287 vertical border (right edge):")
print("=" * 60)

# Find gaps in Python render
print("\nGaps in Python render at x=1287:")
in_gap = False
gap_start = None
for y in range(16, 970):
    ts_black = get_rgb(ts_pixels[1287, y]) == (0, 0, 0)
    py_black = get_rgb(py_pixels[1287, y]) == (0, 0, 0)

    if ts_black and not py_black:
        if not in_gap:
            gap_start = y
            in_gap = True
    elif in_gap:
        print(f"  Gap from y={gap_start} to y={y - 1} ({y - gap_start} pixels)")
        in_gap = False

if in_gap:
    print(f"  Gap from y={gap_start} to y=969 ({970 - gap_start} pixels)")

# Check specific regions
print("\nWeek header area (y=16-86):")
for y in range(16, 87, 10):
    ts_black = get_rgb(ts_pixels[1287, y]) == (0, 0, 0)
    py_black = get_rgb(py_pixels[1287, y]) == (0, 0, 0)
    print(f"  y={y}: TS={ts_black}, Python={py_black}")

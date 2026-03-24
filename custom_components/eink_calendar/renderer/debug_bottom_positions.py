#!/usr/bin/env python3
"""Check bottom border position at multiple x coordinates."""

from PIL import Image

# Load the Python render
img = Image.open("../comparison_tests/empty_calendar_python.png")
pixels = img.load()

# Check bottom border at multiple x positions
x_positions = [15, 200, 400, 600, 800, 1000, 1288]

print("Checking bottom border positions (looking for black pixels):")
print("=" * 60)

for x in x_positions:
    print(f"\nAt x={x}:")
    # Check from y=965 to y=970
    for y in range(965, 971):
        pixel_raw = pixels[x, y]  # pyright: ignore[reportOptionalSubscript]
        if not isinstance(pixel_raw, tuple) or len(pixel_raw) < 3:
            continue
        r, g, b = int(pixel_raw[0]), int(pixel_raw[1]), int(pixel_raw[2])
        is_black = (r, g, b) == (0, 0, 0)
        marker = " <-- BLACK" if is_black else ""
        print(f"  y={y}: RGB({r:3d}, {g:3d}, {b:3d}){marker}")

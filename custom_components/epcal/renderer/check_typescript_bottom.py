#!/usr/bin/env python3
"""Check TypeScript bottom border position."""

from PIL import Image

# Load the TypeScript render
img = Image.open("../comparison_tests/empty_calendar_typescript.png")
pixels = img.load()

# Check bottom border at multiple x positions
x_positions = [15, 200, 400, 600, 800, 1000, 1288]

print("TypeScript bottom border positions:")
print("=" * 60)

for x in x_positions:
    print(f"\nAt x={x}:")
    # Check from y=965 to y=970
    for y in range(965, 971):
        pixel_raw = pixels[x, y]  # pyright: ignore[reportOptionalSubscript]
        if not isinstance(pixel_raw, tuple):
            continue
        if len(pixel_raw) == 4:
            r, g, b, a = (
                int(pixel_raw[0]),
                int(pixel_raw[1]),
                int(pixel_raw[2]),
                int(pixel_raw[3]),
            )
        else:
            r, g, b = int(pixel_raw[0]), int(pixel_raw[1]), int(pixel_raw[2])
        is_black = (r, g, b) == (0, 0, 0)
        marker = " <-- BLACK" if is_black else ""
        print(f"  y={y}: RGB({r:3d}, {g:3d}, {b:3d}){marker}")

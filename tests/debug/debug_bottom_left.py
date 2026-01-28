#!/usr/bin/env python3
from PIL import Image

py = Image.open("comparison_tests/empty_calendar_python.png")

# Check the bottom-left corner where Today section's border should be
# Today section is x=0-400, bottom border should be at y=967-968

print("Bottom-left corner of Today section (x=15-17, y=966-970):")
for y in range(966, 971):
    row = []
    for x in range(14, 18):
        pixel = py.getpixel((x, y))
        if pixel[0] < 50:
            row.append("██")
        else:
            row.append("  ")
    print(f"y={y}: {' '.join(row)}")

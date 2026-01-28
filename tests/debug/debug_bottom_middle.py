#!/usr/bin/env python3
from PIL import Image

py = Image.open("comparison_tests/empty_calendar_python.png")

print("Bottom border at different x positions:")
for x_pos in [15, 200, 400, 600, 800, 1000]:
    print(f"\nx={x_pos}:")
    for y in range(966, 971):
        pixel = py.getpixel((x_pos, y))
        if pixel[0] < 50:
            print(f"  y={y}: BLACK")

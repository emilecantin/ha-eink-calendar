#!/usr/bin/env python3
from PIL import Image

py = Image.open("comparison_tests/empty_calendar_python.png")
ts = Image.open("comparison_tests/empty_calendar_typescript.png")

print("Today/Week border (should be at x=399-400):")
print("Python:")
for x in range(397, 403):
    pixel = py.getpixel((x, 100))
    if pixel[0] < 50:
        print(f"  x={x}: BLACK")

print("\nTypeScript:")
for x in range(397, 403):
    pixel = ts.getpixel((x, 100))
    if pixel[0] < 50:
        print(f"  x={x}: BLACK")

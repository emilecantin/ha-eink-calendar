#!/usr/bin/env python3
from PIL import Image

py = Image.open("comparison_tests/empty_calendar_python.png")

# Check the Sunday/SAT header red section - should be at far right
# Sunday column should be around x=1200
print("Checking Sunday (SAT) red header section:")
print("Top border area (y=14-18):")
for y in range(14, 19):
    pixel = py.getpixel((1200, y))
    if pixel[0] > 200 and pixel[1] < 50:
        print(f"  y={y}: RED")
    elif pixel[0] < 50:
        print(f"  y={y}: BLACK")
    else:
        print(f"  y={y}: WHITE (gap!)")

print("\nLeft border area (x=399-403 where today/week sections meet):")
for x in range(399, 404):
    pixel = py.getpixel((x, 100))
    if pixel[0] < 50:
        print(f"  x={x}: BLACK")
    else:
        print(f"  x={x}: WHITE (gap!)")

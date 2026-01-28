#!/usr/bin/env python3
from PIL import Image

py = Image.open("comparison_tests/empty_calendar_python.png")
ts = Image.open("comparison_tests/empty_calendar_typescript.png")

# Check bottom borders - Week section ends at y=700, Upcoming starts there
print("Bottom border of Week section (y=698-704):")
print("Python at x=600:")
for y in range(698, 704):
    pixel = py.getpixel((600, y))
    if pixel[0] < 50:
        print(f"  y={y}: BLACK")

print("\nTypeScript at x=600:")
for y in range(698, 704):
    pixel = ts.getpixel((600, y))
    if pixel[0] < 50:
        print(f"  y={y}: BLACK")

# Check the very bottom border of the display
print("\n\nBottom of display (y=966-970, margin=16 so should be at 984-16=968):")
print("Python at x=600:")
for y in range(966, 970):
    pixel = py.getpixel((600, y))
    if pixel[0] < 50:
        print(f"  y={y}: BLACK")

print("\nTypeScript at x=600:")
for y in range(966, 970):
    pixel = ts.getpixel((600, y))
    if pixel[0] < 50:
        print(f"  y={y}: BLACK")

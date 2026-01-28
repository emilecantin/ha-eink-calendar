#!/usr/bin/env python3
from PIL import Image, ImageDraw

img = Image.new("RGB", (100, 1000), (255, 255, 255))
draw = ImageDraw.Draw(img)

# Vertical line from y=15 to y=968
draw.line([(50, 15), (50, 968)], fill=(0, 0, 0), width=2)

print("Vertical line from y=15 to y=968 with width=2:")
print("At bottom (y=966-970):")
for y in range(966, 971):
    if img.getpixel((50, y))[0] < 128:
        print(f"  y={y}: BLACK")

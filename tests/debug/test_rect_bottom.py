#!/usr/bin/env python3
from PIL import Image, ImageDraw

img = Image.new("RGB", (100, 100), (255, 255, 255))
draw = ImageDraw.Draw(img)

# Test: rectangle ending at y=50 with width=2
draw.rectangle([(10, 10), (90, 50)], outline=(0, 0, 0), width=2)

print("Rectangle [(10, 10), (90, 50)] with width=2:")
print("Bottom edge pixels:")
for y in range(48, 52):
    if img.getpixel((50, y))[0] < 128:
        print(f"  y={y}: BLACK")

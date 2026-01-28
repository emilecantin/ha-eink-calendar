#!/usr/bin/env python3
from PIL import Image, ImageDraw

# Test with actual coordinates
img = Image.new("RGB", (1304, 984), (255, 255, 255))
draw = ImageDraw.Draw(img)

margin = 16
section_width = 400
section_height = 984

# Draw the actual rectangle
draw.rectangle(
    [(margin - 1, margin - 1), (section_width, section_height - margin)],
    outline=(0, 0, 0),
    width=2,
)

print(f"Rectangle: [(15, 15), (400, {section_height - margin})]")
print(f"Bottom coordinate: {section_height - margin}")
print("\nBottom edge pixels at x=200:")
for y in range(966, 971):
    if img.getpixel((200, y))[0] < 128:
        print(f"  y={y}: BLACK")

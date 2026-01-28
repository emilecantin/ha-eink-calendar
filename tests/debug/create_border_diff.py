#!/usr/bin/env python3
"""Create a visual diff highlighting border differences."""

from PIL import Image

# Load both images
ts_img = Image.open("comparison_tests/empty_calendar_typescript.png").convert("RGB")
py_img = Image.open("comparison_tests/empty_calendar_python.png").convert("RGB")
ts_pixels = ts_img.load()
py_pixels = py_img.load()

# Create diff image
diff_img = Image.new("RGB", ts_img.size, (255, 255, 255))
diff_pixels = diff_img.load()

# Mark differences in red
for y in range(ts_img.height):
    for x in range(ts_img.width):
        ts_rgb = ts_pixels[x, y]
        py_rgb = py_pixels[x, y]

        if ts_rgb != py_rgb:
            # Red for differences
            diff_pixels[x, y] = (255, 0, 0)
        elif ts_rgb == (0, 0, 0):
            # Keep black pixels as black
            diff_pixels[x, y] = (0, 0, 0)

# Save diff
diff_img.save("comparison_tests/border_diff.png")
print("Border diff saved to: comparison_tests/border_diff.png")

# Count differences in border regions
print("\nBorder region differences:")

# Top border (y=14-18)
top_diff = sum(
    1
    for y in range(14, 19)
    for x in range(ts_img.width)
    if ts_pixels[x, y] != py_pixels[x, y]
)
print(f"  Top (y=14-18): {top_diff} different pixels")

# Bottom border (y=966-970)
bottom_diff = sum(
    1
    for y in range(966, 971)
    for x in range(ts_img.width)
    if ts_pixels[x, y] != py_pixels[x, y]
)
print(f"  Bottom (y=966-970): {bottom_diff} different pixels")

# Left border (x=14-18)
left_diff = sum(
    1
    for y in range(ts_img.height)
    for x in range(14, 19)
    if ts_pixels[x, y] != py_pixels[x, y]
)
print(f"  Left (x=14-18): {left_diff} different pixels")

# Right border (x=1286-1290)
right_diff = sum(
    1
    for y in range(ts_img.height)
    for x in range(1286, 1291)
    if ts_pixels[x, y] != py_pixels[x, y]
)
print(f"  Right (x=1286-1290): {right_diff} different pixels")

# Vertical divider (x=398-402)
divider_diff = sum(
    1
    for y in range(ts_img.height)
    for x in range(398, 403)
    if ts_pixels[x, y] != py_pixels[x, y]
)
print(f"  Vertical divider (x=398-402): {divider_diff} different pixels")

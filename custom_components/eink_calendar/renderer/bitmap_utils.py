"""Bitmap conversion utilities for e-paper display."""

import hashlib

from PIL import Image


def image_to_1bit(img: Image.Image, is_red_layer: bool = False) -> bytes:
    """Convert PIL Image to 1-bit packed bitmap for e-paper.

    E-paper format: 0 = colored (black/red), 1 = white/transparent.
    Bitmap starts as all 0xFF (white), colored pixels clear bits to 0.

    Args:
        img: PIL Image in RGB mode
        is_red_layer: If True, extract red pixels, otherwise black pixels

    Returns:
        Packed 1-bit bitmap (0 = colored, 1 = white)
    """
    width, height = img.size
    pixels = img.load()

    # Calculate packed size (8 pixels per byte, MSB first)
    bytes_per_row = (width + 7) // 8
    bitmap = bytearray(b'\xff' * (bytes_per_row * height))

    for y in range(height):
        for x in range(width):
            pixel_raw = pixels[x, y]  # pyright: ignore[reportOptionalSubscript]
            if not isinstance(pixel_raw, tuple) or len(pixel_raw) < 3:
                continue
            r, g, b = int(pixel_raw[0]), int(pixel_raw[1]), int(pixel_raw[2])

            is_red_color = r > 150 and g < 100 and b < 100

            if is_red_layer:
                is_colored = is_red_color
            else:
                # Black layer: dark pixels that aren't red
                brightness = (r + g + b) / 3
                is_colored = brightness < 170 and not is_red_color

            if is_colored:
                byte_index = y * bytes_per_row + x // 8
                bit_index = 7 - (x % 8)  # MSB first
                bitmap[byte_index] &= ~(1 << bit_index)

    return bytes(bitmap)


def extract_chunk(bitmap: bytes, width: int, height: int, top_half: bool) -> bytes:
    """Extract top or bottom half of bitmap.

    Args:
        bitmap: Full bitmap data
        width: Image width in pixels
        height: Image height in pixels
        top_half: If True, extract top half, otherwise bottom half

    Returns:
        Half of the bitmap
    """
    bytes_per_row = (width + 7) // 8
    half_height = height // 2

    if top_half:
        # Extract first half_height rows
        return bitmap[: bytes_per_row * half_height]
    else:
        # Extract last half_height rows
        return bitmap[bytes_per_row * half_height :]


def rotate_image_90cw(img: Image.Image) -> Image.Image:
    """Rotate image 90 degrees clockwise."""
    return img.rotate(-90, expand=True)


def calculate_etag(black_layer: bytes, red_layer: bytes) -> str:
    """Calculate ETag hash for caching."""
    hasher = hashlib.md5()
    hasher.update(black_layer)
    hasher.update(red_layer)
    return hasher.hexdigest()

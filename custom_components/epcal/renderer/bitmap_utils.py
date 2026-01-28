"""Bitmap conversion utilities for e-paper display."""

import hashlib

from PIL import Image


def image_to_1bit(img: Image.Image, is_red_layer: bool = False) -> bytes:
    """Convert PIL Image to 1-bit packed bitmap for e-paper.

    Args:
        img: PIL Image in RGB mode
        is_red_layer: If True, converts red pixels to 1, otherwise black pixels to 1

    Returns:
        Packed 1-bit bitmap (1 = black/red, 0 = white)
    """
    width, height = img.size
    pixels = img.load()

    # Calculate packed size (8 pixels per byte, MSB first)
    bytes_per_row = (width + 7) // 8
    bitmap = bytearray(bytes_per_row * height)

    for y in range(height):
        for x in range(width):
            pixel_raw = pixels[x, y]  # pyright: ignore[reportOptionalSubscript]
            if not isinstance(pixel_raw, tuple) or len(pixel_raw) < 3:
                continue
            r, g, b = int(pixel_raw[0]), int(pixel_raw[1]), int(pixel_raw[2])

            # Determine if pixel should be set
            if is_red_layer:
                # Red layer: set if pixel is red-ish
                is_set = r > 200 and g < 100 and b < 100
            else:
                # Black layer: set if pixel is dark
                is_set = r < 128 and g < 128 and b < 128

            if is_set:
                byte_index = y * bytes_per_row + x // 8
                bit_index = 7 - (x % 8)  # MSB first
                bitmap[byte_index] |= 1 << bit_index

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

"""Bitmap conversion utilities for e-paper display."""

import hashlib

import numpy as np
from PIL import Image


def image_to_1bit(img: Image.Image, is_red_layer: bool = False) -> bytes:
    """Convert PIL Image to 1-bit packed bitmap for e-paper.

    E-paper format: 0 = colored (black/red), 1 = white/transparent.
    Uses NumPy vectorized operations for performance.

    Args:
        img: PIL Image in RGB mode
        is_red_layer: If True, extract red pixels, otherwise black pixels

    Returns:
        Packed 1-bit bitmap (0 = colored, 1 = white)
    """
    width, height = img.size
    arr = np.array(img)  # shape: (height, width, 3+)

    r = arr[:, :, 0].astype(np.float64)
    g = arr[:, :, 1].astype(np.float64)
    b = arr[:, :, 2].astype(np.float64)

    is_red_color = (r > 150) & (g < 100) & (b < 100)

    if is_red_layer:
        is_colored = is_red_color
    else:
        brightness = (r + g + b) / 3.0
        is_colored = (brightness < 170) & ~is_red_color

    # E-paper: 1 = white, 0 = colored -> invert the mask
    white_bits = ~is_colored  # True = white (bit=1)

    # Pad width to multiple of 8 for packbits
    pad_cols = (-width) % 8
    if pad_cols:
        white_bits = np.pad(
            white_bits, ((0, 0), (0, pad_cols)), constant_values=True
        )

    # Pack bits MSB-first: each group of 8 bools -> 1 byte
    packed = np.packbits(white_bits.astype(np.uint8), axis=1)

    return packed.tobytes()


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

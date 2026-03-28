"""Icon rendering utilities for E-Ink Calendar renderer.

Renders MDI (Material Design Icons) using the bundled webfont TTF.
Icons are rendered as font glyphs via Pillow, scaling cleanly to any size.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

_LOGGER = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).parent / "fonts"
MDI_FONT_PATH = FONTS_DIR / "materialdesignicons-webfont.ttf"
MDI_CODEPOINTS_PATH = FONTS_DIR / "mdi_codepoints.json"

# Default icon size in pixels
DEFAULT_ICON_SIZE = 24

# Codepoint lookup: icon name -> hex codepoint string
_codepoints: dict[str, str] | None = None


def _load_codepoints() -> dict[str, str]:
    """Load the MDI name-to-codepoint mapping."""
    global _codepoints
    if _codepoints is not None:
        return _codepoints
    try:
        with open(MDI_CODEPOINTS_PATH) as f:
            _codepoints = json.load(f)
    except Exception as e:
        _LOGGER.error("Failed to load MDI codepoints: %s", e)
        _codepoints = {}
    return _codepoints


@lru_cache(maxsize=32)
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get the MDI font at a given size, cached via lru_cache."""
    return ImageFont.truetype(str(MDI_FONT_PATH), size)


def _render_glyph(
    codepoint_hex: str,
    size: int = DEFAULT_ICON_SIZE,
    color: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> Image.Image:
    """Render a single MDI glyph to an RGBA image."""
    char = chr(int(codepoint_hex, 16))
    font = _get_font(size)

    # Measure the glyph
    bbox = font.getbbox(char)
    if not bbox:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Render glyph onto a tight canvas
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    glyph = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glyph)
    draw.fontmode = "1"  # 1-bit rendering, crisp for e-ink
    draw.text((-bbox[0], -bbox[1]), char, fill=color, font=font)

    # Center glyph in a square canvas (no stretching)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    paste_x = (size - w) // 2
    paste_y = (size - h) // 2
    img.paste(glyph, (paste_x, paste_y), glyph)

    return img


@lru_cache(maxsize=128)
def get_icon(
    icon_name: str,
    size: int = DEFAULT_ICON_SIZE,
    color: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> Optional[Image.Image]:
    """Get an MDI icon rendered as a PIL Image.

    Cached via functools.lru_cache with bounded size to prevent unbounded
    memory growth from rendered icon images.

    Args:
        icon_name: Icon name without prefix (e.g., "calendar", "briefcase")
        size: Pixel size to render at
        color: RGBA color tuple

    Returns:
        PIL RGBA Image, or None if icon not found
    """
    codepoints = _load_codepoints()
    cp = codepoints.get(icon_name)
    if cp is None:
        _LOGGER.warning("MDI icon not found: %s", icon_name)
        return None

    return _render_glyph(cp, size, color)


def paste_icon(
    img: Image.Image,
    icon_name: str,
    x: int,
    y: int,
    size: int = DEFAULT_ICON_SIZE,
    color: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> bool:
    """Paste an icon onto an image at the specified position.

    Args:
        img: Target PIL Image
        icon_name: Icon name without prefix
        x: X coordinate (left edge)
        y: Y coordinate (top edge)
        size: Icon size in pixels
        color: RGBA color tuple

    Returns:
        True if successful, False if icon not found
    """
    icon = get_icon(icon_name, size, color)
    if icon is None:
        return False

    try:
        img.paste(icon, (x, y), icon)
        return True
    except Exception as e:
        _LOGGER.error("Error pasting icon %s: %s", icon_name, e)
        return False


# Icon name mapping for weather conditions
WEATHER_ICON_NAMES = {
    "sunny": "weather-sunny",
    "clear": "weather-sunny",
    "clear-night": "weather-night",
    "partlycloudy": "weather-partly-cloudy",
    "cloudy": "weather-cloudy",
    "fog": "weather-fog",
    "hail": "weather-hail",
    "lightning": "weather-lightning",
    "lightning-rainy": "weather-lightning-rainy",
    "pouring": "weather-pouring",
    "rainy": "weather-rainy",
    "snowy": "weather-snowy",
    "snowy-rainy": "weather-snowy-rainy",
    "windy": "weather-windy",
    "windy-variant": "weather-windy",
    "exceptional": "weather-hurricane",
}


def get_weather_icon(
    condition: str, size: int = DEFAULT_ICON_SIZE
) -> Optional[Image.Image]:
    """Get a weather icon by HA weather condition name."""
    icon_name = WEATHER_ICON_NAMES.get(condition)
    if icon_name:
        return get_icon(icon_name, size)
    return None


def get_mdi_icon(
    mdi_string: str,
    size: int = DEFAULT_ICON_SIZE,
    fallback: str = "calendar",
) -> Optional[Image.Image]:
    """Get an MDI icon from HA icon string format (e.g., "mdi:briefcase")."""
    icon_name = mdi_string.removeprefix("mdi:")

    icon = get_icon(icon_name, size)
    if icon is None and fallback:
        icon = get_icon(fallback, size)
    return icon


def create_inverted_icon(icon: Image.Image) -> Image.Image:
    """Create a white version of an RGBA icon with opacity-based anti-aliasing.

    Takes an icon rendered as black/gray on transparent background and returns
    a white version suitable for pasting onto colored backgrounds (e.g., red
    weekend headers on e-paper).

    The logic:
    1. Convert RGB to grayscale
    2. Invert grayscale (black->white mapping gives opacity)
    3. Multiply with original alpha to preserve transparency
    4. Apply as alpha to a pure white image

    Args:
        icon: RGBA PIL Image with black/gray pixels on transparent background

    Returns:
        RGBA PIL Image with white pixels and combined alpha
    """
    _r, _g, _b, a = icon.split()
    gray = icon.convert("L")
    inverted_gray = ImageOps.invert(gray)
    combined_alpha = ImageChops.multiply(inverted_gray, a)
    white_icon = Image.new("RGBA", icon.size, (255, 255, 255, 255))
    white_icon.putalpha(combined_alpha)
    return white_icon


def list_available_icons() -> list[str]:
    """List all available MDI icon names."""
    return sorted(_load_codepoints().keys())

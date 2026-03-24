"""Font loading utilities."""

import logging
from pathlib import Path

from PIL import ImageFont

from .types import FontDict, RenderOptions

_LOGGER = logging.getLogger(__name__)

# Font cache
_font_cache = {}


def load_font(
    font_path: str | None, size: int, weight: str = "Regular"
) -> ImageFont.FreeTypeFont:
    """Load a font with caching.

    Args:
        font_path: Path to custom font file, or None to use bundled Inter
        size: Font size in pixels
        weight: Font weight (Regular, Medium, Bold)

    Returns:
        ImageFont.FreeTypeFont object
    """
    cache_key = (font_path, size, weight)

    if cache_key in _font_cache:
        return _font_cache[cache_key]

    font = None

    # Try custom font path first
    if font_path:
        try:
            font = ImageFont.truetype(font_path, size)
            _LOGGER.debug("Loaded custom font: %s (size %d)", font_path, size)
        except Exception as err:
            _LOGGER.warning("Failed to load custom font %s: %s", font_path, err)

    # Fall back to bundled Inter font
    if font is None:
        try:
            # Get path to bundled fonts (in renderer/fonts/)
            module_dir = Path(__file__).parent
            font_file = module_dir / "fonts" / f"Inter-{weight}.ttf"
            font = ImageFont.truetype(str(font_file), size)
            _LOGGER.debug("Loaded bundled font: Inter-%s (size %d)", weight, size)
        except Exception as err:
            _LOGGER.warning("Failed to load bundled font: %s", err)

    # Last resort: system default font
    if font is None:
        try:
            default_font = ImageFont.load_default()
            # load_default() returns ImageFont, but we need FreeTypeFont
            # This is a fallback case that should rarely happen
            _LOGGER.warning("Using system default font (size %d)", size)
            # Type ignore because we're accepting ImageFont as fallback
            font = default_font  # type: ignore[assignment]
        except Exception as err:
            _LOGGER.error("Failed to load any font: %s", err)
            raise

    _font_cache[cache_key] = font
    return font  # pyright: ignore[reportReturnType]


def get_fonts(options: RenderOptions) -> FontDict:
    """Get all font variants needed for rendering.

    Returns dict with structure:
    {
        "regular": {14: font, 16: font, ...},
        "medium": {18: font, 20: font, ...},
        "bold": {18: font, 22: font, ...},
    }
    """
    regular_path = options.get("font_regular")
    medium_path = options.get("font_medium")
    bold_path = options.get("font_bold")

    return {
        "regular": {
            14: load_font(regular_path, 14, "Regular"),
            16: load_font(regular_path, 16, "Regular"),
            18: load_font(regular_path, 18, "Regular"),
            20: load_font(regular_path, 20, "Regular"),
            32: load_font(regular_path, 32, "Regular"),  # For weather icons
            44: load_font(regular_path, 44, "Regular"),  # For large weather icons
        },
        "medium": {
            18: load_font(medium_path, 18, "Medium"),
            20: load_font(medium_path, 20, "Medium"),
            22: load_font(medium_path, 22, "Medium"),
        },
        "bold": {
            14: load_font(bold_path, 14, "Bold"),
            16: load_font(bold_path, 16, "Bold"),
            18: load_font(bold_path, 18, "Bold"),
            20: load_font(bold_path, 20, "Bold"),
            22: load_font(bold_path, 22, "Bold"),
            24: load_font(bold_path, 24, "Bold"),
            28: load_font(bold_path, 28, "Bold"),
            32: load_font(bold_path, 32, "Bold"),
        },
    }

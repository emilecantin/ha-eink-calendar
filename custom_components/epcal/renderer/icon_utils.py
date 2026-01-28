"""
Icon rendering utilities for EPCAL renderer.

This module provides utilities for loading and rendering MDI (Material Design Icons)
PNG icons that were pre-generated from SVG sources.
"""

from pathlib import Path
from typing import Optional

from PIL import Image

# Directory containing the pre-generated icon PNGs
ICON_DIR = Path(__file__).parent / "icons"

# Cache for loaded icons to avoid repeated file I/O
_icon_cache = {}


def get_icon(icon_name: str) -> Optional[Image.Image]:
    """
    Load an icon PNG file and return it as a PIL Image.

    Args:
        icon_name: The name of the icon (without .png extension)
                  e.g., "weather-sunny", "calendar", "briefcase"

    Returns:
        PIL Image object if found, None if not found

    Example:
        >>> icon = get_icon("weather-sunny")
        >>> if icon:
        ...     img.paste(icon, (x, y), icon)  # Paste with alpha mask
    """
    if icon_name in _icon_cache:
        return _icon_cache[icon_name]

    icon_path = ICON_DIR / f"{icon_name}.png"

    if not icon_path.exists():
        print(f"Warning: Icon not found: {icon_name}.png")
        return None

    try:
        icon = Image.open(icon_path).convert("RGBA")
        _icon_cache[icon_name] = icon
        return icon
    except Exception as e:
        print(f"Error loading icon {icon_name}: {e}")
        return None


def paste_icon(
    img: Image.Image,
    icon_name: str,
    x: int,
    y: int,
    color: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> bool:
    """
    Paste an icon onto an image at the specified position.

    The icon is loaded and pasted with transparency support. You can optionally
    colorize the icon by providing a color tuple.

    Args:
        img: The PIL Image to paste the icon onto
        icon_name: The name of the icon (without .png extension)
        x: X coordinate (left edge)
        y: Y coordinate (top edge)
        color: RGBA color tuple for the icon (default: black)

    Returns:
        True if successful, False if icon not found or error occurred

    Example:
        >>> from PIL import Image
        >>> img = Image.new("RGB", (100, 100), "white")
        >>> paste_icon(img, "weather-sunny", 10, 10)
        True
    """
    icon = get_icon(icon_name)
    if icon is None:
        return False

    try:
        # Create a colored version of the icon if color is specified
        if color != (0, 0, 0, 255):
            # Create a colored overlay
            colored = Image.new("RGBA", icon.size, color)
            # Use the icon's alpha channel as a mask
            colored.putalpha(icon.split()[3])  # Use original alpha
            icon = colored

        # Paste with alpha channel as mask for transparency
        img.paste(icon, (x, y), icon)
        return True
    except Exception as e:
        print(f"Error pasting icon {icon_name}: {e}")
        return False


def list_available_icons():
    """
    List all available icon names.

    Returns:
        List of icon names (without .png extension)

    Example:
        >>> icons = list_available_icons()
        >>> print(icons[:5])
        ['weather-sunny', 'weather-cloudy', 'calendar', 'briefcase', 'home']
    """
    if not ICON_DIR.exists():
        return []

    return sorted([f.stem for f in ICON_DIR.glob("*.png")])


# Icon name mapping for common use cases
WEATHER_ICON_NAMES = {
    "sunny": "weather-sunny",
    "clear": "weather-sunny",
    "clear-night": "weather-clear-night",
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
    "exceptional": "weather-exceptional",
}


def get_weather_icon(condition: str) -> Optional[Image.Image]:
    """
    Get a weather icon by Home Assistant weather condition name.

    Args:
        condition: Home Assistant weather condition
                  (e.g., "sunny", "cloudy", "rainy")

    Returns:
        PIL Image object if found, None if not found

    Example:
        >>> icon = get_weather_icon("sunny")
        >>> if icon:
        ...     img.paste(icon, (x, y), icon)
    """
    icon_name = WEATHER_ICON_NAMES.get(condition)
    if icon_name:
        return get_icon(icon_name)
    return None


def get_mdi_icon(mdi_string: str, fallback: str = "calendar") -> Optional[Image.Image]:
    """
    Get an MDI icon from Home Assistant icon string format.

    Args:
        mdi_string: Icon string in format "mdi:icon-name"
                   e.g., "mdi:briefcase", "mdi:calendar", "mdi:home"
        fallback: Icon name to use if the requested icon isn't found (default: "calendar")

    Returns:
        PIL Image object if found (or fallback icon), None only if fallback also fails

    Example:
        >>> icon = get_mdi_icon("mdi:briefcase")
        >>> if icon:
        ...     img.paste(icon, (x, y), icon)
    """
    # Handle "mdi:icon-name" format
    if mdi_string.startswith("mdi:"):
        icon_name = mdi_string[4:]  # Remove "mdi:" prefix
    else:
        # If it's already just the icon name
        icon_name = mdi_string

    # Try to get the requested icon
    icon = get_icon(icon_name)

    # If not found and fallback is specified, try fallback
    if icon is None and fallback:
        icon = get_icon(fallback)

    return icon


# Legacy helper functions for compatibility with existing code
def get_icon_center_offset(icon_text: str, icon_font) -> int:
    """
    Legacy function for calculating icon center offset.

    This was used when icons were rendered as text. Now returns 0
    since PNG icons are positioned directly.

    Args:
        icon_text: Icon text (no longer used)
        icon_font: Font (no longer used)

    Returns:
        0 (PNG icons don't need offset adjustment)
    """
    return 0


def get_icon_bottom_offset(icon_text: str, icon_font) -> int:
    """
    Legacy function for calculating icon bottom offset.

    This was used when icons were rendered as text. Now returns 0
    since PNG icons are positioned directly.

    Args:
        icon_text: Icon text (no longer used)
        icon_font: Font (no longer used)

    Returns:
        0 (PNG icons don't need offset adjustment)
    """
    return 0

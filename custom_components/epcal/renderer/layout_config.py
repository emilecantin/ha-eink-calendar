"""Layout configuration constants for EPCAL e-paper calendar rendering.

Centralizes all magic numbers for display dimensions, typography, spacing, and layout.
"""

# Display dimensions
DISPLAY = {
    "PORTRAIT": {"width": 984, "height": 1304},
    "LANDSCAPE": {"width": 1304, "height": 984},
}

# Margins and spacing
MARGINS = {
    "STANDARD": 16,
    "SECTION_PADDING": 10,
    "HEADER_SPACING": 8,
}

# Portrait layout sections
LAYOUT_PORTRAIT = {
    "TODAY": {
        "y": 0,
        "height": 450,
    },
    "WEEK": {
        "y": 450,
        "height": 600,
    },
    "UPCOMING": {
        "y": 1050,
        "height": 254,
    },
}

# Landscape layout sections
LAYOUT_LANDSCAPE = {
    "TODAY": {
        "x": 0,
        "width": 400,
    },
    "RIGHT_PANEL": {
        "x": 400,
        "width": 904,
    },
    "WEEK": {
        "y": 0,
        "height": 700,
    },
    "UPCOMING": {
        "y": 700,
        "height": 284,
    },
}

# Typography sizes
TYPOGRAPHY = {
    "HEADER_LARGE": 28,
    "HEADER_MEDIUM": 24,
    "HEADER_SMALL": 22,
    "EVENT_TIME": 20,
    "EVENT_TITLE": 20,
    "EVENT_TITLE_SMALL": 16,
    "DAY_NUMBER": 32,
    "DAY_NAME": 18,
    "OVERFLOW": 18,
    "OVERFLOW_SMALL": 14,
    "LEGEND_TEXT": 14,
    "WEATHER_TEMP": 18,
    "WEATHER_TEMP_LARGE": 24,
}

# Icon sizes
ICON_SIZES = {
    "TODAY_SECTION": 18,
    "WEEK_SECTION": 14,
    "WEATHER_LARGE": 44,
    "WEATHER_MEDIUM": 32,
    "WEATHER_SMALL": 24,
    "COLLECTION_ICON": 18,
}

# Event dimensions
EVENT_DIMENSIONS = {
    "HEIGHT_PORTRAIT": 36,
    "HEIGHT_LANDSCAPE_TODAY": 36,
    "HEIGHT_LANDSCAPE_WEEK": 30,
    "LINE_HEIGHT": 22,
    "TITLE_LINE_HEIGHT": 18,
    "TIME_WIDTH": 60,
    "TRIANGLE_SIZE": 6,
}

# Colors
COLORS = {
    "BLACK": (0, 0, 0),
    "WHITE": (255, 255, 255),
    "RED": (255, 0, 0),
    "GRAY_WEEKEND": (240, 240, 240),
}

# Miscellaneous layout constants
LAYOUT_MISC = {
    "LEGEND_MAX_COLUMNS": 2,
    "LEGEND_MAX_ITEMS": 8,
    "LEGEND_ITEM_HEIGHT": 20,
    "LEGEND_COLUMN_WIDTH": 175,
    "WEATHER_SPACING": 10,
    "DAY_COLUMN_HEADER_HEIGHT": 60,
    "WEEK_VIEW_DAYS": 6,
}

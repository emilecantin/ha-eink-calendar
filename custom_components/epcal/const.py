"""Constants for the E-Paper Calendar integration."""

DOMAIN = "epcal"

# Default configuration
DEFAULT_NAME = "E-Paper Calendar"
DEFAULT_LAYOUT = "landscape"
DEFAULT_SHOW_LEGEND = True

# Entity naming
CAMERA_NAME = "preview"
SENSOR_LAST_UPDATE_NAME = "last_update"
IMAGE_BLACK_TOP_NAME = "black_layer_top"
IMAGE_BLACK_BOTTOM_NAME = "black_layer_bottom"
IMAGE_RED_TOP_NAME = "red_layer_top"
IMAGE_RED_BOTTOM_NAME = "red_layer_bottom"

# Configuration keys
CONF_DEVICE_NAME = "device_name"
CONF_CALENDARS = "calendars"
CONF_WASTE_CALENDARS = "waste_calendars"
CONF_LAYOUT = "layout"
CONF_SHOW_LEGEND = "show_legend"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_FONT_REGULAR = "font_regular"
CONF_FONT_MEDIUM = "font_medium"
CONF_FONT_BOLD = "font_bold"

# Layout options
LAYOUT_LANDSCAPE = "landscape"
LAYOUT_PORTRAIT = "portrait"

# Services
SERVICE_REFRESH = "refresh"

# MDI icon to Unicode symbol mapping for calendar icons
MDI_TO_UNICODE = {
    "mdi:calendar": "●",
    "mdi:briefcase": "■",
    "mdi:home": "▲",
    "mdi:school": "◆",
    "mdi:heart": "♥",
    "mdi:star": "★",
    "mdi:flag": "⚑",
    "mdi:trophy": "🏆",
    "mdi:cake": "🎂",
    "mdi:gift": "🎁",
    "mdi:phone": "☎",
    "mdi:email": "✉",
    "mdi:car": "🚗",
    "mdi:airplane": "✈",
    "mdi:account": "👤",
    "mdi:account-multiple": "👥",
}

"""Constants for the E-Paper Calendar integration."""

DOMAIN = "eink_calendar"

# Default configuration
DEFAULT_NAME = "E-Ink Calendar"
DEFAULT_LAYOUT = "landscape"
DEFAULT_SHOW_LEGEND = True
DEFAULT_REFRESH_INTERVAL = 15  # minutes

# Entity naming
CAMERA_NAME = "preview"
SENSOR_LAST_UPDATE_NAME = "last_update"
SENSOR_LAST_CHECKIN_NAME = "last_checkin"
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
CONF_MAC_ADDRESS = "mac_address"
CONF_FIRMWARE_VERSION = "firmware_version"
CONF_REFRESH_INTERVAL = "refresh_interval"

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

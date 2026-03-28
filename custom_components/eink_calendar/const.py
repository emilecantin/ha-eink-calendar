"""Constants for the E-Paper Calendar integration."""

DOMAIN = "eink_calendar"

# Default configuration
DEFAULT_NAME = "E-Ink Calendar"
DEFAULT_LAYOUT = "landscape"
DEFAULT_SHOW_LEGEND = True
DEFAULT_LANGUAGE = "fr"
DEFAULT_REFRESH_INTERVAL = 15  # minutes

# Entity naming
CAMERA_NAME = "preview"
SENSOR_LAST_UPDATE_NAME = "last_update"
SENSOR_LAST_CHECKIN_NAME = "last_checkin"
SENSOR_FIRMWARE_VERSION_NAME = "firmware_version"
SENSOR_DEVICE_STATUS_NAME = "device_status"
SENSOR_DEVICE_ETAG_NAME = "device_etag"
SENSOR_CHECKIN_COUNT_NAME = "checkin_count"
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
CONF_LANGUAGE = "language"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_WASTE_ICON_MAP = "waste_icon_map"

# Layout options
LAYOUT_LANDSCAPE = "landscape"
LAYOUT_PORTRAIT = "portrait"

# Services
SERVICE_REFRESH = "refresh"

# Firmware
FIRMWARE_MANAGER_KEY = "firmware_manager"

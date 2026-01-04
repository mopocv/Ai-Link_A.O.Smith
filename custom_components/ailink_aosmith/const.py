"""Constants for Ai-Link A.O. Smith integration."""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfVolume

# Integration domain/brand
DOMAIN = "ailink_aosmith"
BRAND = "Ai-Link A.O. Smith"

# Configuration keys (config entry + options)
CONF_ACCESS_TOKEN = "access_token"
CONF_USER_ID = "user_id"
CONF_FAMILY_ID = "family_id"
CONF_DEVICE_ID = "device_id"
CONF_MOBILE = "mobile"
CONF_COOKIE = "cookie"
CONF_LANGUAGE = "language"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ENABLE_RAW_SENSORS = "enable_raw_sensors"

# Default values
DEFAULT_NAME = "Ai-Link A.O. Smith Water Heater"
DEFAULT_LANGUAGE = "zh-Hans"
DEFAULT_UPDATE_INTERVAL = 60
DEFAULT_ENABLE_RAW_SENSORS = True

# Platforms provided by this integration
PLATFORMS = ["water_heater", "sensor", "switch"]

# Coordinator update interval (seconds)
UPDATE_INTERVAL = DEFAULT_UPDATE_INTERVAL

# Device category that identifies water heaters (string or numeric in APIs)
DEVICE_CATEGORY_WATER_HEATER = "19"

# Water heater temperature limits (product range may vary — these are HA limits)
WATER_HEATER_MIN_TEMP = 35.0
WATER_HEATER_MAX_TEMP = 70.0
WATER_HEATER_DEFAULT_TEMP = 38.0
WATER_HEATER_TEMP_PRECISION = 1.0

# Cruise timer limits (minutes)
CRUISE_TIMER_MIN = 1
CRUISE_TIMER_MAX = 99
CRUISE_TIMER_STEP = 1

# HTTP / API defaults
API_BASE_URL = "https://ailink-api.hotwater.com.cn"

# Switch types
SWITCH_TYPE_CRUISE = "cruise"
SWITCH_TYPE_HALF_PIPE = "half_pipe"

# Misc
LOG_NAMESPACE = "custom_components.ailink_aosmith"

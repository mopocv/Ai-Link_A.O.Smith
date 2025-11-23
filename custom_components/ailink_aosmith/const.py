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

# Default values
DEFAULT_NAME = "Ai-Link A.O. Smith Water Heater"

# Platforms provided by this integration
PLATFORMS = ["water_heater", "sensor", "valve"]

# Coordinator update interval (seconds)
UPDATE_INTERVAL = 60

# Device category that identifies water heaters (string or numeric in APIs)
DEVICE_CATEGORY_WATER_HEATER = "19"

# Water heater temperature limits (product range may vary — these are HA limits)
WATER_HEATER_MIN_TEMP = 35.0
WATER_HEATER_MAX_TEMP = 70.0
WATER_HEATER_DEFAULT_TEMP = 38.0
WATER_HEATER_TEMP_PRECISION = 1.0

# HTTP / API defaults
API_BASE_URL = "https://ailink-api.hotwater.com.cn"

# Switch types
SWITCH_TYPE_PRESSURIZE = "pressurize"
SWITCH_TYPE_CRUISE = "cruise"
SWITCH_TYPE_HALF_PIPE = "half_pipe"

# Valve types
VALVE_TYPE_CRUISE = "cruise"
VALVE_TYPE_HALF_PIPE = "half_pipe"

# Misc
LOG_NAMESPACE = "custom_components.ailink_aosmith"
"""Constants for Ai-Link A.O. Smith integration."""
from homeassistant.components.sensor import SensorDeviceClass

DOMAIN = "ailink_aosmith"
BRAND = "Ai-Link A.O. Smith"

# Configuration keys
CONF_ACCESS_TOKEN = "access_token"
CONF_USER_ID = "user_id"
CONF_FAMILY_ID = "family_id"
CONF_DEVICE_ID = "device_id"
CONF_MOBILE = "mobile"
CONF_COOKIE = "cookie"

# Default values
DEFAULT_NAME = "Ai-Link A.O. Smith Water Heater"

# Platform
PLATFORMS = ["water_heater", "sensor"]

# Update interval for coordinator
UPDATE_INTERVAL = 60  # seconds

# Device categories
DEVICE_CATEGORY_WATER_HEATER = "19"

# 默认空 SENSOR_TYPES，改为在 sensor.py 中根据 JSON 动态加载
SENSOR_TYPES = {}

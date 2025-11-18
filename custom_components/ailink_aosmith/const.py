"""Constants for Ai-Link A.O. Smith integration."""
DOMAIN = "ailink_aosmith"
BRAND = "Ai-Link A.O. Smith"

# Configuration
CONF_ACCESS_TOKEN = "access_token"
CONF_USER_ID = "user_id"
CONF_FAMILY_ID = "family_id"
CONF_DEVICE_ID = "device_id"
CONF_MOBILE = "mobile"
CONF_COOKIE = "cookie"  # 新增 Cookie 配置

# Default values
DEFAULT_NAME = "Ai-Link A.O. Smith Water Heater"

# Sensor types
SENSOR_TYPES = {
    "water_temp": ["Current Temperature", "°C", "mdi:thermometer"],
    "in_water_temp": ["Inlet Temperature", "°C", "mdi:thermometer"],
    "out_water_temp": ["Outlet Temperature", "°C", "mdi:thermometer"],
    "water_flow": ["Water Flow", "L/min", "mdi:water-pump"],
    "fire_times": ["Ignition Count", None, "mdi:fire"],
    "total_water_num": ["Total Water Used", "L", "mdi:water"],
    "total_gas_num": ["Total Gas Used", "units", "mdi:fire"],
    "fan_speed": ["Fan Speed", "RPM", "mdi:fan"],
    "co_concentration": ["CO Concentration", "ppm", "mdi:molecule-co"],
    "device_status": ["Device Status", None, "mdi:information"],
    "power_status": ["Power Status", None, "mdi:power"],
}
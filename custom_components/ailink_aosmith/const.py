"""Constants for Ai-Link A.O. Smith integration."""
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfVolume

DOMAIN = "ailink_aosmith"
BRAND = "Ai-Link A.O. Smith"

# Configuration
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

# Sensor types - updated structure with device class
SENSOR_TYPES = {
    "water_temp": ["Current Temperature", UnitOfTemperature.CELSIUS, "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    "in_water_temp": ["Inlet Temperature", UnitOfTemperature.CELSIUS, "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    "out_water_temp": ["Outlet Temperature", UnitOfTemperature.CELSIUS, "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    "water_flow": ["Water Flow", "L/min", "mdi:water-pump", None],
    "fire_times": ["Ignition Count", None, "mdi:fire", None],
    "total_water_num": ["Total Water Used", UnitOfVolume.LITERS, "mdi:water", None],
    "total_gas_num": ["Total Gas Used", "units", "mdi:fire", None],
    "fan_speed": ["Fan Speed", "RPM", "mdi:fan", None],
    "co_concentration": ["CO Concentration", "ppm", "mdi:molecule-co", SensorDeviceClass.CO],
    "device_status": ["Device Status", None, "mdi:information", None],
    "power_status": ["Power Status", None, "mdi:power", None],
}

# Water heater operations
WATER_HEATER_OPERATIONS = ["off", "heat"]

# Device categories
DEVICE_CATEGORY_WATER_HEATER = "19"
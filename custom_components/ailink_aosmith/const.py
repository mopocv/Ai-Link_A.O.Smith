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
    # key: [翻译key, 单位翻译key, mdi图标, 设备类型]
    "water_temp": ["sensor.water_temp", "unit_of_measurement.water_temp", "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    "in_water_temp": ["sensor.in_water_temp", "unit_of_measurement.in_water_temp", "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    "out_water_temp": ["sensor.out_water_temp", "unit_of_measurement.out_water_temp", "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    "hot_water_temp": ["sensor.hot_water_temp", "unit_of_measurement.hot_water_temp", "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    "fan_current": ["sensor.fan_current", "unit_of_measurement.fan_current", "mdi:current-ac", None],
    "fan_speed": ["sensor.fan_speed", "unit_of_measurement.fan_speed", "mdi:fan", None],
    "fire_times": ["sensor.fire_times", "unit_of_measurement.fire_times", "mdi:fire", None],
    "total_water_num": ["sensor.total_water_num", "unit_of_measurement.total_water_num", "mdi:water", None],
    "total_gas_num": ["sensor.total_gas_num", "unit_of_measurement.total_gas_num", "mdi:fire", None],
    "cruising_total_gas_num": ["sensor.cruising_total_gas_num", "unit_of_measurement.cruising_total_gas_num", "mdi:counter", None],
    "sec_all_buring_time": ["sensor.sec_all_buring_time", "unit_of_measurement.sec_all_buring_time", "mdi:timer", None],
    "sec_all_fire_num": ["sensor.sec_all_fire_num", "unit_of_measurement.sec_all_fire_num", "mdi:counter", None],
    "sec_pump_operating_fre": ["sensor.sec_pump_operating_fre", "unit_of_measurement.sec_pump_operating_fre", "mdi:speedometer", None],
    "gas_pressure": ["sensor.gas_pressure", "unit_of_measurement.gas_pressure", "mdi:gauge", None],
    "water_hardness": ["sensor.water_hardness", "unit_of_measurement.water_hardness", "mdi:potable-water", None],
    "device_status": ["sensor.device_status", "unit_of_measurement.device_status", "mdi:information", None],
    "power_status": ["sensor.power_status", "unit_of_measurement.power_status", "mdi:power", None],
    "error_code": ["sensor.error_code", "unit_of_measurement.error_code", "mdi:alert", None],
    "co_concentration": ["sensor.co_concentration", "unit_of_measurement.co_concentration", "mdi:molecule-co", SensorDeviceClass.CO],
    "out_water_temp": ["sensor.out_water_temp", "unit_of_measurement.out_water_temp", "mdi:thermometer", SensorDeviceClass.TEMPERATURE],
    # 更多字段可按 outputData 自动补全...
}

# Water heater operations
WATER_HEATER_OPERATIONS = ["off", "heat"]

# Device categories
DEVICE_CATEGORY_WATER_HEATER = "19"
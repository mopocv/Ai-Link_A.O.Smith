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
PLATFORMS = ["water_heater", "sensor", "switch"]

# Coordinator update interval (seconds)
UPDATE_INTERVAL = 60

# Device category that identifies water heaters (string or numeric in APIs)
DEVICE_CATEGORY_WATER_HEATER = "19"

# Water heater supported operations (internal keys)
# These are internal-mode keys used in code; translations live in translations/*.json
WATER_HEATER_OPERATION_KEYS = ["off", "heat", "cruise_on", "half_pipe_cruise", "eco"]

# Water heater temperature limits (product range may vary — these are HA limits)
WATER_HEATER_MIN_TEMP = 35.0
WATER_HEATER_MAX_TEMP = 70.0
WATER_HEATER_DEFAULT_TEMP = 40.0
WATER_HEATER_TEMP_PRECISION = 1.0

# Common outputData fields observed in device.statusInfo
# Use these keys when mapping sensors or parsing status
COMMON_OUTPUT_KEYS = {
    # temperatures
    "waterTemp",
    "inWaterTemp",
    "outWaterTemp",
    "hotWaterTemp",

    # flow / volumes
    "waterFlow",
    "totalWaterNum",
    "secLitre",

    # gas / combustion
    "fireTimes",
    "totalGasNum",
    "cruisingTotalGasNum",
    "secAllBuringTime",
    "secAllFireNum",
    "fireWorkTime",
    "secDutyProportion",
    "gasPressure",
    "cruisingGasShow",

    # pump / fan / electrical
    "fanSpeed",
    "fanCurrent",
    "secPumpOperatingFre",
    "secPumpRunningCurrent",
    "secAdjustMaxCurrent",
    "secAdjustMinCurrent",

    # water quality / softener
    "waterHardness",
    "nowTDS",
    "neutralizerLife",
    "saltRegenerationTimes",

    # device / power / status / errors
    "deviceStatus",  # 1 = running, 0 = off
    "powerStatus",   # 1 = power on, 0 = power off
    "errorCode",
    "waterErrorCode",
    "cOConcentration",
    "cOSensorAlarm",
    "cOAlarmSignal",

    # cruise / zero-cold-water related
    "cruiseStatus",
    "secAllCirAntifreeNum",
    "secAllFirCirAntifreeNum",
    "secWindPressureZeroValue",
    "secAntiWindPressNum",

    # meta / firmware / version
    "secVersionCode",
    "mainBoardVersion",
    "hardwareVersion",
}

# Value mapping helpers - keys that often represent boolean-like states ("1"/"0")
BOOLEAN_LIKE_KEYS = {
    "powerStatus",
    "deviceStatus",
    "powerOn",
    "pumpRunning",
    "cruiseStatus",
    "appTiming",
    "fastHeatStatus",
}

# Default icons (fallbacks) used by sensor creation logic (can be overridden by translations)
DEFAULT_ICONS = {
    "temperature": "mdi:thermometer",
    "flow": "mdi:water-pump",
    "gas": "mdi:fire",
    "fan": "mdi:fan",
    "electric": "mdi:current-ac",
    "info": "mdi:information-outline",
    "error": "mdi:alert",
    "counter": "mdi:counter",
    "timer": "mdi:timer",
}

# HTTP / API defaults (if needed by API client)
API_BASE_URL = "https://ailink-api.hotwater.com.cn"
API_INVOKE_PATH = "/AiLinkService/device/invokeMethod"
API_GET_DEVICES = "/AiLinkService/appDevice/getHomepageV2"
API_GET_DEVICE_STATUS = "/AiLinkService/appDevice/getDeviceCurrInfo"

# Misc
LOG_NAMESPACE = "custom_components.ailink_aosmith"

"""Platform for sensor integration."""
import logging
import json

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfVolume

from .const import DOMAIN, SENSOR_TYPES
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Ai-Link A.O. Smith sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Wait for initial data to be loaded
    await coordinator.async_config_entry_first_refresh()
    
    entities = []
    for device_id, device_data in coordinator.data.items():
        # 兼容 deviceCategory 为字符串或数字
        category = device_data.get("deviceCategory")
        if str(category) == "19":  # Water heater device category
            for sensor_type in SENSOR_TYPES:
                entities.append(AOSmithSensor(coordinator, device_id, sensor_type))
    
    _LOGGER.info("Setting up %d sensor entities", len(entities))
    async_add_entities(entities, True)

class AOSmithSensor(AOSmithEntity, SensorEntity):
    """Representation of an Ai-Link A.O. Smith sensor."""
    
    def __init__(self, coordinator, device_id, sensor_type):
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._sensor_type = sensor_type
        self._device_id = device_id
        self._sensor_type = sensor_type
        
        name, unit, icon, device_class = SENSOR_TYPES[sensor_type]
        # 如果 productName 为 None，使用默认名
        product_name = self.device_data.get('productName') or 'A.O. Smith'
        self._attr_name = f"{product_name} {name}"
        self._attr_unique_id = f"ailink_aosmith_{sensor_type}_{device_id}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        
        # HomeKit compatibility - ensure state_class is set for appropriate sensors
        if device_class in [SensorDeviceClass.TEMPERATURE, SensorDeviceClass.CO]:
            self._attr_state_class = "measurement"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._get_sensor_value()
    
    def _get_sensor_value(self):
        """Get the sensor value from device data."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
            
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    
                    # Map sensor types to data fields
                    sensor_mapping = {
                        "water_temp": self._get_float_value(output_data, "waterTemp"),
                        "in_water_temp": self._get_float_value(output_data, "inWaterTemp"),
                        "out_water_temp": self._get_float_value(output_data, "outWaterTemp"), 
                        "water_flow": self._get_float_value(output_data, "waterFlow"),
                        "fire_times": self._get_int_value(output_data, "fireTimes"),
                        "total_water_num": self._get_int_value(output_data, "totalWaterNum"),
                        "total_gas_num": self._get_int_value(output_data, "totalGasNum"),
                        "fan_speed": self._get_int_value(output_data, "fanSpeed"),
                        "co_concentration": self._get_float_value(output_data, "cOConcentration"),
                        "device_status": self._get_device_status(output_data),
                        "power_status": self._get_power_status(output_data),
                    }
                    
                    value = sensor_mapping.get(self._sensor_type)
                    
                    # Ensure numeric values for HomeKit compatibility
                    if value is None and self._sensor_type in ["water_temp", "in_water_temp", "out_water_temp"]:
                        return 0.0
                    
                    return value
                    
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error parsing status info for sensor %s: %s", self._sensor_type, e)
            
        return None
    
    def _get_float_value(self, data, key):
        """Get float value from data."""
        value = data.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _get_int_value(self, data, key):
        """Get int value from data."""
        value = data.get(key)
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _get_device_status(self, data):
        """Get device status as readable string."""
        status = data.get("deviceStatus")
        if status == "1":
            return "Online"
        elif status == "0":
            return "Offline"
        return "Unknown"
    
    def _get_power_status(self, data):
        """Get power status as readable string."""
        status = data.get("powerStatus")
        if status == "1":
            return "On"
        elif status == "0":
            return "Off"
        return "Unknown"
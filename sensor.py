"""Platform for sensor integration."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import TEMP_CELSIUS, VOLUME_LITERS_PER_MINUTE

from .const import DOMAIN, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up A.O. Smith sensor platform."""
    api = hass.data[DOMAIN][config_entry.entry_id]
    device_id = config_entry.data.get("device_id")
    
    if not device_id:
        _LOGGER.error("No device ID configured")
        return
    
    # Create sensors for each type
    entities = []
    for sensor_type in SENSOR_TYPES:
        entities.append(AOSmithSensor(api, device_id, sensor_type))
    
    async_add_entities(entities, True)

class AOSmithSensor(SensorEntity):
    """Representation of an A.O. Smith sensor."""
    
    def __init__(self, api, device_id, sensor_type):
        """Initialize the sensor."""
        self._api = api
        self._device_id = device_id
        self._sensor_type = sensor_type
        
        name, unit, icon = SENSOR_TYPES[sensor_type]
        self._attr_name = f"A.O. Smith {name}"
        self._attr_unique_id = f"aosmith_{sensor_type}_{device_id}"
        self._attr_unit_of_measurement = unit
        self._attr_icon = icon
        
        self._state = None
    
    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
    
    async def async_update(self):
        """Fetch new state data for the sensor."""
        status = await self._api.async_get_device_status(self._device_id)
        
        if status and "appDeviceStatusInfoEntity" in status:
            status_entity = status["appDeviceStatusInfoEntity"]
            status_info = status_entity.get("statusInfo", "")
            
            if status_info:
                await self._parse_status_info(status_info)
    
    async def _parse_status_info(self, status_info: str):
        """Parse the status info JSON."""
        import json
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    
                    # Map sensor types to data fields
                    sensor_mapping = {
                        "water_temp": output_data.get("waterTemp"),
                        "in_water_temp": output_data.get("inWaterTemp"),
                        "out_water_temp": output_data.get("outWaterTemp"), 
                        "water_flow": output_data.get("waterFlow"),
                        "fire_times": output_data.get("fireTimes"),
                        "total_water_num": output_data.get("totalWaterNum"),
                        "total_gas_num": output_data.get("totalGasNum"),
                        "fan_speed": output_data.get("fanSpeed"),
                        "co_concentration": output_data.get("cOConcentration"),
                        "device_status": output_data.get("deviceStatus"),
                        "power_status": output_data.get("powerStatus"),
                    }
                    
                    self._state = sensor_mapping.get(self._sensor_type)
                    
        except json.JSONDecodeError as e:
            _LOGGER.error("Failed to parse status info JSON for sensor %s: %s", self._sensor_type, e)
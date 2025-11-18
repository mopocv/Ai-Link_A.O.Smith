"""Platform for water_heater integration."""
import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    STATE_ECO,
    STATE_PERFORMANCE,
    SUPPORT_OPERATION_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_OPERATION_MODE | SUPPORT_TARGET_TEMPERATURE
OPERATION_MODES = [STATE_ECO, STATE_PERFORMANCE]

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Ai-Link A.O. Smith water_heater platform."""
    api = hass.data[DOMAIN][config_entry.entry_id]
    
    # Get device ID from config
    device_id = config_entry.data.get("device_id")
    
    if device_id:
        # Get device details
        devices = await api.async_get_devices()
        device = next((d for d in devices if d["deviceId"] == device_id), None)
        
        if device:
            entities = [AOSmithWaterHeater(api, device)]
            async_add_entities(entities, True)
        else:
            _LOGGER.error("Device %s not found in device list", device_id)
    else:
        _LOGGER.error("No device ID configured")

class AOSmithWaterHeater(WaterHeaterEntity):
    """Representation of an Ai-Link A.O. Smith water heater."""
    
    def __init__(self, api, device):
        """Initialize the water heater."""
        self._api = api
        self._device = device
        self._device_id = device["deviceId"]
        self._attr_name = device.get("deviceName", "Ai-Link A.O. Smith Water Heater")
        self._attr_unique_id = f"ailink_aosmith_water_heater_{self._device_id}"
        
        self._current_temperature = None
        self._target_temperature = None
        self._operation_mode = STATE_ECO
        self._attributes = {}
        
        # Set device info for HA
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._attr_name,
            "manufacturer": "A.O. Smith",
            "model": device.get("productModel", "Unknown"),
            "sw_version": device.get("firmwareVersion", "Unknown"),
        }
    
    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS
    
    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS
    
    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature
    
    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature
    
    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 35  # Typical minimum for gas water heaters
    
    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 60  # Typical maximum for gas water heaters
    
    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return OPERATION_MODES
    
    @property
    def current_operation(self):
        """Return current operation mode."""
        return self._operation_mode
    
    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes
    
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            # This would need to be implemented once we find the control API
            _LOGGER.info("Would set temperature to %s for device %s", temperature, self._device_id)
            self._target_temperature = temperature
    
    async def async_set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        # This would need to be implemented once we find the control API
        _LOGGER.info("Would set operation mode to %s for device %s", operation_mode, self._device_id)
        self._operation_mode = operation_mode
    
    async def async_update(self):
        """Fetch new state data for the water heater."""
        status = await self._api.async_get_device_status(self._device_id)
        
        if status and "appDeviceStatusInfoEntity" in status:
            status_entity = status["appDeviceStatusInfoEntity"]
            status_info = status_entity.get("statusInfo", "")
            
            if status_info:
                await self._parse_status_info(status_info)
        
        # Also update device info from space mapping if available
        if "appSpaceDeviceMappingEntity" in status:
            space_info = status["appSpaceDeviceMappingEntity"]
            if space_info.get("roomName"):
                self._attributes["location"] = space_info["roomName"]
    
    async def _parse_status_info(self, status_info: str):
        """Parse the status info JSON."""
        import json
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    
                    # Extract temperature data
                    self._current_temperature = self._safe_int(output_data.get("waterTemp"))
                    self._target_temperature = self._safe_int(output_data.get("waterTemp"))
                    
                    # Determine operation mode based on power status
                    power_status = output_data.get("powerStatus")
                    device_status = output_data.get("deviceStatus")
                    
                    if power_status == "1" and device_status == 1:
                        self._operation_mode = STATE_PERFORMANCE
                    else:
                        self._operation_mode = STATE_ECO
                    
                    # Extract additional attributes
                    self._attributes.update({
                        "water_flow": output_data.get("waterFlow"),
                        "in_water_temp": output_data.get("inWaterTemp"),
                        "out_water_temp": output_data.get("outWaterTemp"),
                        "fire_times": output_data.get("fireTimes"),
                        "fan_speed": output_data.get("fanSpeed"),
                        "device_status": device_status,
                        "power_status": power_status,
                        "error_code": output_data.get("errorCode"),
                        "co_concentration": output_data.get("cOConcentration"),
                        "total_water_num": output_data.get("totalWaterNum"),
                        "total_gas_num": output_data.get("totalGasNum"),
                        "work_status": output_data.get("workStatus"),
                        "cruise_status": output_data.get("cruiseStatus"),
                    })
                    
        except json.JSONDecodeError as e:
            _LOGGER.error("Failed to parse status info JSON for device %s: %s", self._device_id, e)
    
    def _safe_int(self, value):
        """Safely convert to integer."""
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None
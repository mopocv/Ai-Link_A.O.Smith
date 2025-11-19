"""Support for A.O. Smith water heaters."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up A.O. Smith water heater from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Wait for initial data to be loaded
    await coordinator.async_config_entry_first_refresh()
    
    entities = []
    for device_id in coordinator.data:
        device_data = coordinator.data[device_id]
        # Only create water heater entities for actual water heater devices
        if device_data.get("deviceCategory") == "19":  # Water heater device category
            entities.append(AOSmithWaterHeater(coordinator, device_id))
    
    _LOGGER.info("Setting up %d water heater entities", len(entities))
    async_add_entities(entities)

class AOSmithWaterHeater(AOSmithEntity, WaterHeaterEntity):
    """Representation of an A.O. Smith water heater."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = ["off", "heat"]

    def __init__(self, coordinator, device_id):
        """Initialize the water heater."""
        super().__init__(coordinator, device_id)
        self._attr_name = self.device_data.get("productName", "A.O. Smith Water Heater")
        self._attr_unique_id = f"{device_id}_water_heater"
        
        # Set supported features for HomeKit compatibility
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE | 
            WaterHeaterEntityFeature.OPERATION_MODE
        )
        
        # HomeKit specific attributes
        self._attr_precision = 1.0  # Temperature precision for HomeKit

    @property
    def current_operation(self) -> str | None:
        """Return current operation."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return "off"
            
        try:
            status_data = json.loads(status_info)
            events = status_data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    # Check if device is heating based on water temperature
                    water_temp = self._get_float_value(output_data, "waterTemp")
                    power_status = output_data.get("powerStatus")
                    
                    # HomeKit expects "heat" when actively heating
                    if power_status == "1" and water_temp is not None and water_temp > 0:
                        return "heat"
            return "off"
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error parsing status info for %s: %s", self.device_id, e)
            return "off"

    @property
    def current_temperature(self) -> float | None:
        """Return the current water temperature."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
            
        try:
            status_data = json.loads(status_info)
            events = status_data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    temp = self._get_float_value(output_data, "waterTemp")
                    # HomeKit requires temperature values
                    return temp if temp is not None else 0.0
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error getting current temperature for %s: %s", self.device_id, e)
            
        return 0.0  # Default for HomeKit compatibility

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        # For HomeKit, we need to return a target temperature
        # If we don't have a specific target, use current temperature
        current_temp = self.current_temperature
        if current_temp is not None:
            return current_temp
            
        # Fallback for HomeKit
        return 40.0

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return 35.0  # HomeKit compatible minimum

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return 75.0  # HomeKit compatible maximum

    def _get_float_value(self, data: dict, key: str) -> float | None:
        """Safely get a float value from dictionary."""
        value = data.get(key)
        if value is None:
            return None
            
        try:
            return float(value)
        except (ValueError, TypeError):
            _LOGGER.debug("Cannot convert %s to float for key %s", value, key)
            return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            _LOGGER.info("Setting temperature for %s to %s", self.device_id, temperature)
            # TODO: Implement API call to set temperature
            # For now, update the coordinator data to reflect the change
            self.device_data["target_temperature"] = temperature
            self.async_write_ha_state()
            _LOGGER.warning("Temperature setting not yet implemented for device %s", self.device_id)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode."""
        _LOGGER.info("Setting operation mode for %s to %s", self.device_id, operation_mode)
        # TODO: Implement API call to set operation mode
        # For now, update the coordinator data to reflect the change
        self.device_data["operation_mode"] = operation_mode
        self.async_write_ha_state()
        _LOGGER.warning("Operation mode setting not yet implemented for device %s", self.device_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}
        
        status_info = self.device_data.get("statusInfo")
        if status_info:
            try:
                status_data = json.loads(status_info)
                events = status_data.get("events", [])
                for event in events:
                    if event.get("identifier") == "post":
                        output_data = event.get("outputData", {})
                        
                        # Add relevant status information as attributes
                        attrs["water_flow"] = self._get_float_value(output_data, "waterFlow")
                        attrs["in_water_temp"] = self._get_float_value(output_data, "inWaterTemp")
                        attrs["out_water_temp"] = self._get_float_value(output_data, "outWaterTemp")
                        attrs["fire_work_time"] = output_data.get("fireWorkTime")
                        attrs["total_water_num"] = output_data.get("totalWaterNum")
                        attrs["error_code"] = output_data.get("errorCode")
                        
                        # HomeKit friendly attributes
                        attrs["power_status"] = output_data.get("powerStatus")
                        attrs["device_status"] = output_data.get("deviceStatus")
                        break
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                _LOGGER.debug("Error parsing status info for attributes: %s", e)
        
        return attrs
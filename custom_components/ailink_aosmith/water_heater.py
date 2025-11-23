"""Support for A.O. Smith water heaters with HomeKit valve service support."""
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

from .const import DOMAIN, WATER_HEATER_MIN_TEMP, WATER_HEATER_MAX_TEMP, WATER_HEATER_DEFAULT_TEMP, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up A.O. Smith water heater entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            entities.append(AOSmithWaterHeater(coordinator, device_id))

    _LOGGER.info("Setting up %d water heater entities", len(entities))
    async_add_entities(entities, True)


class AOSmithWaterHeater(AOSmithEntity, WaterHeaterEntity):
    """A.O. Smith water heater with HomeKit valve service support."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, device_id: str):
        """Initialize the water heater."""
        super().__init__(coordinator, device_id)
        self._attr_name = self.device_data.get("productName", "A.O. Smith Water Heater")
        self._attr_unique_id = f"{device_id}_water_heater"
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
        )
        self._attr_precision = 1.0
        self._power_state = False
        self._cruise_state = False
        self._half_pipe_state = False

    def _update_states_from_data(self):
        """Update internal states from device data."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return
            
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    
                    # Update power state
                    power_status = output_data.get("powerStatus")
                    self._power_state = power_status == "1"
                    
                    # Update cruise state (零冷水)
                    cruise_status = output_data.get("cruiseStatus")
                    self._cruise_state = cruise_status == "1"
                    
                    # Update half pipe state (节能半管)
                    # 可能需要根据实际API字段调整
                    half_pipe_status = output_data.get("halfPipeStatus")
                    self._half_pipe_state = half_pipe_status == "1"
                    
                    break
        except Exception as e:
            _LOGGER.debug("Error updating states from data for %s: %s", self._device_id, e)

    @property
    def current_operation(self) -> str:
        """Return current operation mode."""
        self._update_states_from_data()
        
        if not self._power_state:
            return "off"
        
        # Build operation description based on active states
        states = []
        if self._cruise_state:
            states.append("巡航")
        if self._half_pipe_state:
            states.append("节能半管")
        
        if states:
            return " | ".join(states)
        else:
            return "加热"

    @property
    def current_temperature(self) -> float | None:
        """Return current water temperature."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    val = event.get("outputData", {}).get("waterTemp")
                    if val is not None:
                        return float(val)
        except Exception as e:
            _LOGGER.debug("Error getting current temperature for %s: %s", self._device_id, e)
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        # Try to get from device data first
        target_temp = self.device_data.get("target_temperature")
        if target_temp is not None:
            return float(target_temp)
        
        # Fall back to current temperature or default
        current_temp = self.current_temperature
        if current_temp is not None:
            return current_temp
            
        return WATER_HEATER_DEFAULT_TEMP

    @property
    def min_temp(self) -> float:
        return WATER_HEATER_MIN_TEMP

    @property
    def max_temp(self) -> float:
        return WATER_HEATER_MAX_TEMP

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            _LOGGER.info("Setting temperature for %s to %s°C", self._device_id, temperature)
            
            # Update local state immediately for responsiveness
            self.device_data["target_temperature"] = temperature
            self.async_write_ha_state()
            
            # Send command to device
            try:
                await self.coordinator.api.async_send_command(
                    self._device_id, 
                    "WaterTempSet", 
                    {"waterTemp": str(int(temperature))}
                )
                _LOGGER.info("Temperature set command sent successfully for %s", self._device_id)
            except Exception as e:
                _LOGGER.error("Failed to set temperature for %s: %s", self._device_id, e)
                # Revert local state on error
                self.device_data.pop("target_temperature", None)
                self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the water heater on."""
        _LOGGER.info("Turning on water heater %s", self._device_id)
        try:
            await self.coordinator.api.async_send_command(
                self._device_id, 
                "PowerOnOff", 
                {"powerStatus": "1"}
            )
            self._power_state = True
            self.async_write_ha_state()
            _LOGGER.info("Water heater %s turned on", self._device_id)
        except Exception as e:
            _LOGGER.error("Failed to turn on water heater %s: %s", self._device_id, e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the water heater off."""
        _LOGGER.info("Turning off water heater %s", self._device_id)
        try:
            await self.coordinator.api.async_send_command(
                self._device_id, 
                "PowerOnOff", 
                {"powerStatus": "0"}
            )
            self._power_state = False
            self.async_write_ha_state()
            _LOGGER.info("Water heater %s turned off", self._device_id)
        except Exception as e:
            _LOGGER.error("Failed to turn off water heater %s: %s", self._device_id, e)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        self._update_states_from_data()
        
        attrs = {
            "device_id": self._device_id,
            "power_state": "on" if self._power_state else "off",
            "cruise_state": "on" if self._cruise_state else "off",
            "half_pipe_state": "on" if self._half_pipe_state else "off",
        }
        
        status_info = self.device_data.get("statusInfo")
        if status_info:
            try:
                data = json.loads(status_info)
                events = data.get("events", [])
                for event in events:
                    if event.get("identifier") == "post":
                        output_data = event.get("outputData", {})
                        # Add relevant output data as attributes
                        for key in ["waterFlow", "inWaterTemp", "outWaterTemp", "fireWorkTime", 
                                  "totalWaterNum", "errorCode", "powerStatus", "deviceStatus"]:
                            if key in output_data:
                                attrs[key] = output_data[key]
                        break
            except Exception as e:
                _LOGGER.debug("Error parsing status info for attributes: %s", e)
                
        return attrs
"""Support for A.O. Smith water heaters with independent state controls."""
from __future__ import annotations

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
    async_add_entities(entities)


class AOSmithWaterHeater(AOSmithEntity, WaterHeaterEntity):
    """A.O. Smith water heater with independent state controls."""

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
        
        # Initialize state variables
        self._power_state = False
        self._cruise_state = False
        self._half_pipe_state = False
        self._pressurize_state = False

    def _update_states_from_data(self):
        """Update internal states from device data."""
        output_data = self._get_output_data()
        if not output_data:
            return

        power_status = output_data.get("powerStatus")
        self._power_state = power_status == "1"

        cruise_status = output_data.get("cruiseStatus")
        self._cruise_state = cruise_status == "1"

        half_pipe_status = output_data.get("halfPipeStatus")
        if half_pipe_status is None:
            half_pipe_status = output_data.get("setHalfPipeCircle")
        if half_pipe_status is None:
            half_pipe_status = output_data.get("halfPipeCircle")
        self._half_pipe_state = str(half_pipe_status) == "1"

        pressurize_status = output_data.get("pressurizeStatus")
        if pressurize_status is None:
            pressurize_status = output_data.get("pressurize")
        self._pressurize_state = str(pressurize_status) == "1"

    @property
    def current_operation(self) -> str:
        """Return current operation mode."""
        self._update_states_from_data()
        
        if not self._power_state:
            return "off"
        
        # Build operation description based on active states
        states = []
        if self._cruise_state:
            states.append("零冷水")
        if self._half_pipe_state:
            states.append("节能零冷水")
        if self._pressurize_state:
            states.append("增压")
        
        if states:
            return " | ".join(states)
        else:
            return "加热"

    @property
    def current_temperature(self) -> float | None:
        """Return current water temperature."""
        output_data = self._get_output_data()
        if not output_data:
            return None
        val = output_data.get("waterTemp")
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
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
            _LOGGER.info("Setting temperature for %s to %s°C", self.device_id, temperature)
            
            # Update local state immediately for responsiveness
            self.device_data["target_temperature"] = temperature
            self.async_write_ha_state()
            
            # Send command to device
            try:
                await self.coordinator.api.async_send_command(
                    self.device_id, 
                    "WaterTempSet", 
                    {"waterTemp": str(int(temperature))}
                )
                _LOGGER.info("Temperature set command sent successfully for %s", self.device_id)
            except Exception as e:
                _LOGGER.error("Failed to set temperature for %s: %s", self.device_id, e)
                # Revert local state on error
                self.device_data.pop("target_temperature", None)
                self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the water heater on."""
        _LOGGER.info("Turning on water heater %s", self.device_id)
        try:
            await self.coordinator.api.async_send_command(
                self.device_id, 
                "PowerOnOff", 
                {"powerStatus": "1"}
            )
            self._power_state = True
            self.async_write_ha_state()
            _LOGGER.info("Water heater %s turned on", self.device_id)
        except Exception as e:
            _LOGGER.error("Failed to turn on water heater %s: %s", self.device_id, e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the water heater off."""
        _LOGGER.info("Turning off water heater %s", self.device_id)
        try:
            await self.coordinator.api.async_send_command(
                self.device_id, 
                "PowerOnOff", 
                {"powerStatus": "0"}
            )
            self._power_state = False
            self.async_write_ha_state()
            _LOGGER.info("Water heater %s turned off", self.device_id)
        except Exception as e:
            _LOGGER.error("Failed to turn off water heater %s: %s", self.device_id, e)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        self._update_states_from_data()
        
        attrs = {
            "device_id": self.device_id,
            "power_state": "on" if self._power_state else "off",
            "cruise_state": "on" if self._cruise_state else "off",
            "half_pipe_state": "on" if self._half_pipe_state else "off",
            "pressurize_state": "on" if self._pressurize_state else "off",
        }
        
        output_data = self._get_output_data()
        if output_data:
            for key in [
                "waterFlow",
                "inWaterTemp",
                "outWaterTemp",
                "fireWorkTime",
                "totalWaterNum",
                "errorCode",
                "powerStatus",
                "deviceStatus",
                "pressurizeStatus",
            ]:
                if key in output_data:
                    attrs[key] = output_data[key]
                
        return attrs

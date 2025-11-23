"""Support for A.O. Smith zero cold water modes as HomeKit valves."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.valve import (
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up A.O. Smith valve entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            # Add valve entities for zero cold water modes
            entities.extend([
                AOSmithCruiseValve(coordinator, device_id),
                AOSmithHalfPipeValve(coordinator, device_id),
            ])

    _LOGGER.info("Setting up %d valve entities", len(entities))
    async_add_entities(entities, True)


class AOSmithBaseValve(AOSmithEntity, ValveEntity):
    """Base class for A.O. Smith zero cold water valves."""
    
    def __init__(self, coordinator, device_id: str, valve_type: str):
        """Initialize the valve."""
        super().__init__(coordinator, device_id)
        self._valve_type = valve_type
        
        # Get translation configuration
        translation = getattr(coordinator, 'translation', {})
        valve_config = translation.get('entity', {}).get('valve', {}).get(valve_type, {})
        
        device_name = self.device_data.get('productName', 'Water Heater')
        valve_name = valve_config.get('name', valve_type)
        
        self._attr_name = f"{device_name} {valve_name}"
        self._attr_unique_id = f"{device_id}_{valve_type}"
        self._attr_icon = valve_config.get('icon', 'mdi:valve')
        self._attr_supported_features = (
            ValveEntityFeature.OPEN | 
            ValveEntityFeature.CLOSE |
            ValveEntityFeature.STOP
        )
        self._is_active = False

    def _update_state_from_data(self):
        """Update valve state from device data."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return
            
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    self._is_active = self._get_state_from_output(output_data)
                    break
        except Exception as e:
            _LOGGER.debug("Error updating %s state for %s: %s", self._valve_type, self._device_id, e)

    def _get_state_from_output(self, output_data: dict) -> bool:
        """Extract valve state from output data - to be implemented by subclasses."""
        return False

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        self._update_state_from_data()
        return not self._is_active

    @property
    def is_opening(self) -> bool:
        """Return true if valve is opening."""
        return False

    @property
    def is_closing(self) -> bool:
        """Return true if valve is closing."""
        return False

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info("Opening %s for %s", self._valve_type, self._device_id)
        try:
            await self._send_open_command()
            self._is_active = True
            self.async_write_ha_state()
            _LOGGER.info("%s opened for %s", self._valve_type, self._device_id)
        except Exception as e:
            _LOGGER.error("Failed to open %s for %s: %s", self._valve_type, self._device_id, e)

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info("Closing %s for %s", self._valve_type, self._device_id)
        try:
            await self._send_close_command()
            self._is_active = False
            self.async_write_ha_state()
            _LOGGER.info("%s closed for %s", self._valve_type, self._device_id)
        except Exception as e:
            _LOGGER.error("Failed to close %s for %s: %s", self._valve_type, self._device_id, e)

    async def async_stop_valve(self, **kwargs: Any) -> None:
        """Stop the valve."""
        # For zero cold water modes, stopping is the same as closing
        await self.async_close_valve()

    async def _send_open_command(self):
        """Send command to open the valve - to be implemented by subclasses."""
        pass

    async def _send_close_command(self):
        """Send command to close the valve - to be implemented by subclasses."""
        pass


class AOSmithCruiseValve(AOSmithBaseValve):
    """Valve for cruise mode (零冷水)."""
    
    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "cruise")
        self._attr_icon = "mdi:water-sync"

    def _get_state_from_output(self, output_data: dict) -> bool:
        """Get cruise state from output data."""
        cruise_status = output_data.get("cruiseStatus")
        return cruise_status == "1"

    async def _send_open_command(self):
        """Turn on cruise mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "WaterCruiseOnOff", 
            {"cruiseStatus": "1"}
        )

    async def _send_close_command(self):
        """Turn off cruise mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "WaterCruiseOnOff", 
            {"cruiseStatus": "0"}
        )


class AOSmithHalfPipeValve(AOSmithBaseValve):
    """Valve for half pipe mode (节能半管)."""
    
    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "half_pipe")
        self._attr_icon = "mdi:pipe"

    def _get_state_from_output(self, output_data: dict) -> bool:
        """Get half pipe state from output data."""
        # 根据实际API字段调整
        half_pipe_status = output_data.get("halfPipeStatus")
        return half_pipe_status == "1"

    async def _send_open_command(self):
        """Turn on half pipe mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "setHalfPipeCircle", 
            {"setHalfPipeCircle": "1"}
        )

    async def _send_close_command(self):
        """Turn off half pipe mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "setHalfPipeCircle", 
            {"setHalfPipeCircle": "0"}
        )
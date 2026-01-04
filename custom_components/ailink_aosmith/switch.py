"""Support for A.O. Smith independent state switches."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up A.O. Smith switch entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            # Add individual state switches
            entities.extend([
                AOSmithCruiseSwitch(coordinator, device_id),
                AOSmithHalfPipeSwitch(coordinator, device_id),
            ])

    _LOGGER.info("Setting up %d switch entities", len(entities))
    async_add_entities(entities, True)


class AOSmithBaseSwitch(AOSmithEntity, SwitchEntity):
    """Base class for A.O. Smith state switches."""
    
    def __init__(self, coordinator, device_id: str, switch_key: str):
        """Initialize the switch."""
        super().__init__(coordinator, device_id)
        self._switch_key = switch_key
        
        # 从翻译配置获取名称和图标
        translation = getattr(coordinator, 'translation', {})
        _LOGGER.debug("Available translation keys: %s", list(translation.keys()) if translation else "No translation")
        
        switch_config = {}
        if translation:
            entity_config = translation.get('entity', {})
            _LOGGER.debug("Entity config keys: %s", list(entity_config.keys()))
            switch_config = entity_config.get('switch', {}).get(switch_key, {})
            _LOGGER.debug("Switch config for %s: %s", switch_key, switch_config)
        
        device_name = self.device_data.get('productName', 'Water Heater')
        switch_name = switch_config.get('name', switch_key)
        
        self._attr_name = f"{device_name} {switch_name}"
        self._attr_unique_id = f"{device_id}_{switch_key}"
        self._attr_icon = switch_config.get('icon')
        self._is_on = False

    def _update_state_from_data(self):
        """Update switch state from device data."""
        status_info = self._get_status_info()
        if not status_info:
            return
            
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    self._is_on = self._get_state_from_output(output_data)
                    break
        except Exception as e:
            _LOGGER.debug("Error updating %s state for %s: %s", self._switch_key, self._device_id, e)

    def _get_state_from_output(self, output_data: dict) -> bool:
        """Extract switch state from output data - to be implemented by subclasses."""
        return False

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        self._update_state_from_data()
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        _LOGGER.info("Turning on %s for %s", self._switch_key, self._device_id)
        try:
            await self._send_turn_on_command()
            self._is_on = True
            self.async_write_ha_state()
            _LOGGER.info("%s turned on for %s", self._switch_key, self._device_id)
        except Exception as e:
            _LOGGER.error("Failed to turn on %s for %s: %s", self._switch_key, self._device_id, e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        _LOGGER.info("Turning off %s for %s", self._switch_key, self._device_id)
        try:
            await self._send_turn_off_command()
            self._is_on = False
            self.async_write_ha_state()
            _LOGGER.info("%s turned off for %s", self._switch_key, self._device_id)
        except Exception as e:
            _LOGGER.error("Failed to turn off %s for %s: %s", self._switch_key, self._device_id, e)

    async def _send_turn_on_command(self):
        """Send command to turn on the switch - to be implemented by subclasses."""
        pass

    async def _send_turn_off_command(self):
        """Send command to turn off the switch - to be implemented by subclasses."""
        pass


class AOSmithCruiseSwitch(AOSmithBaseSwitch):
    """Switch for cruise mode (零冷水)."""
    
    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "cruise")

    def _get_state_from_output(self, output_data: dict) -> bool:
        """Get cruise state from output data."""
        cruise_status = output_data.get("cruiseStatus")
        return cruise_status == "1"

    async def _send_turn_on_command(self):
        """Turn on cruise mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "WaterCruiseOnOff", 
            {"cruiseStatus": "1"}
        )

    async def _send_turn_off_command(self):
        """Turn off cruise mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "WaterCruiseOnOff", 
            {"cruiseStatus": "0"}
        )


class AOSmithHalfPipeSwitch(AOSmithBaseSwitch):
    """Switch for half pipe mode (节能半管)."""
    
    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "half_pipe")

    def _get_state_from_output(self, output_data: dict) -> bool:
        """Get half pipe state from output data."""
        # 根据实际API字段调整
        half_pipe_status = output_data.get("halfPipeStatus")
        if half_pipe_status is None:
            half_pipe_status = output_data.get("setHalfPipeCircle")
        if half_pipe_status is None:
            half_pipe_status = output_data.get("halfPipeCircle")
        return str(half_pipe_status) == "1"

    async def _send_turn_on_command(self):
        """Turn on half pipe mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "setHalfPipeCircle", 
            {"setHalfPipeCircle": "1"}
        )

    async def _send_turn_off_command(self):
        """Turn off half pipe mode."""
        await self.coordinator.api.async_send_command(
            self._device_id, 
            "setHalfPipeCircle", 
            {"setHalfPipeCircle": "0"}
        )

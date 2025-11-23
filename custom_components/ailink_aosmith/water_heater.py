"""Support for A.O. Smith water heaters with independent state controls."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE, 
    UnitOfTemperature,
    STATE_OFF,
    STATE_HEAT
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, 
    WATER_HEATER_MIN_TEMP, 
    WATER_HEATER_MAX_TEMP, 
    WATER_HEATER_DEFAULT_TEMP, 
    DEVICE_CATEGORY_WATER_HEATER,
    OPERATION_LIST
)
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
    """A.O. Smith water heater simplified for HomeKit compatibility."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = OPERATION_LIST # 使用标准的模式列表 [off, heat]
    
    # 显式声明支持的特性：目标温度 + 模式操作(开关机)
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE | 
        WaterHeaterEntityFeature.OPERATION_MODE
    )

    def __init__(self, coordinator, device_id: str):
        """Initialize the water heater."""
        super().__init__(coordinator, device_id)
        self._attr_name = self.device_data.get("productName", "A.O. Smith Water Heater")
        self._attr_unique_id = f"{device_id}_water_heater"
        self._attr_precision = 1.0
        self._power_state = False

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
                    # 只需要关注电源状态，其他状态交给 switch 实体处理
                    power_status = output_data.get("powerStatus")
                    self._power_state = power_status == "1"
                    break
        except Exception as e:
            _LOGGER.debug("Error updating states from data for %s: %s", self.device_id, e)

    @property
    def current_operation(self) -> str:
        """Return current operation mode strictly for HomeKit."""
        self._update_states_from_data()
        # HomeKit 只需要知道是开(Heat)还是关(Off)
        return STATE_HEAT if self._power_state else STATE_OFF

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
            pass
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        target_temp = self.device_data.get("target_temperature")
        if target_temp is not None:
            return float(target_temp)
        
        # 如果没有缓存的目标温度，尝试读取当前温度作为回退
        # 实际逻辑可能需要从 outputData 获取 setTemp (取决于API是否有这个字段)
        # 这里假设当前出水温度接近设定温度，或者使用默认值
        current_temp = self.current_temperature
        return current_temp if current_temp is not None else WATER_HEATER_DEFAULT_TEMP

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
            # 更新本地状态以便UI立即响应
            self.device_data["target_temperature"] = temperature
            self.async_write_ha_state()
            
            try:
                await self.coordinator.api.async_send_command(
                    self.device_id, 
                    "WaterTempSet", 
                    {"waterTemp": str(int(temperature))}
                )
            except Exception as e:
                _LOGGER.error("Failed to set temperature: %s", e)
                self.device_data.pop("target_temperature", None)
                self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode."""
        if operation_mode == STATE_HEAT:
            await self.async_turn_on()
        elif operation_mode == STATE_OFF:
            await self.async_turn_off()
        else:
            _LOGGER.error("Unsupported operation mode: %s", operation_mode)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the water heater on."""
        try:
            await self.coordinator.api.async_send_command(
                self.device_id, 
                "PowerOnOff", 
                {"powerStatus": "1"}
            )
            self._power_state = True
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to turn on: %s", e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the water heater off."""
        try:
            await self.coordinator.api.async_send_command(
                self.device_id, 
                "PowerOnOff", 
                {"powerStatus": "0"}
            )
            self._power_state = False
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to turn off: %s", e)

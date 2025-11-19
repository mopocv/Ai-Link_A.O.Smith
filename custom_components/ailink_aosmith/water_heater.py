"""Support for A.O. Smith water heaters with temperature and zero cold water mode control."""
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
    """Set up A.O. Smith water heater entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    config_json = getattr(coordinator, "config_json", {})
    operation_mode_map = config_json.get("entity", {}).get("water_heater", {}).get("operation_mode", {})

    entities = []
    for device_id, device_data in coordinator.data.items():
        if device_data.get("deviceCategory") == "19":
            entities.append(AOSmithWaterHeater(coordinator, device_id, operation_mode_map))

    _LOGGER.info("Setting up %d water heater entities", len(entities))
    async_add_entities(entities)


class AOSmithWaterHeater(AOSmithEntity, WaterHeaterEntity):
    """A.O. Smith water heater with temperature and zero cold water modes."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, device_id: str, operation_mode_map: dict):
        super().__init__(coordinator, device_id)
        self._attr_name = self.device_data.get("productName", "A.O. Smith Water Heater")
        self._attr_icon = "mdi:water-boiler"
        self._attr_unique_id = f"{device_id}_water_heater"
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE |
            WaterHeaterEntityFeature.OPERATION_MODE
        )
        self._attr_precision = 1.0
        self._operation_mode_map = operation_mode_map
        self._zero_cold_water_status = "off"  # "one_key" / "half_pipe" / "off"
        self._attr_operation_list = ["off", "heat", "one_key", "half_pipe"]

    def _is_heating(self):
        """Return True if water heater is currently heating."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return False
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    power_status = output_data.get("powerStatus")
                    water_temp = output_data.get("waterTemp")
                    return power_status == "1" and water_temp and float(water_temp) > 0
        except Exception:
            return False
        return False

    @property
    def current_operation(self) -> str:
        """Return current operation mode."""
        if self._zero_cold_water_status != "off":
            return self._zero_cold_water_status
        return "heat" if self._is_heating() else "off"

    @property
    def operation_list(self) -> list[str]:
        """Return supported operation modes."""
        return [self._operation_mode_map.get(op, op) for op in self._attr_operation_list]

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
                    return float(val) if val is not None else 0.0
        except Exception:
            return 0.0

    @property
    def target_temperature(self) -> float | None:
        return float(self.device_data.get("target_temperature", self.current_temperature or 40.0))

    @property
    def min_temp(self) -> float:
        return 35.0

    @property
    def max_temp(self) -> float:
        return 70.0

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self.device_data["target_temperature"] = temperature
            self.async_write_ha_state()
            _LOGGER.info("Setting temperature for %s to %s", self.device_id, temperature)
            # 调用 API 下发温度命令
            if hasattr(self.coordinator, "api"):
                try:
                    await self.coordinator.api.async_set_temperature(self.device_id, temperature)
                except Exception as e:
                    _LOGGER.error("Failed to set temperature for %s: %s", self.device_id, e)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set operation mode including zero cold water modes."""
        internal_mode = None
        if operation_mode in ["one_key", "half_pipe"]:
            internal_mode = operation_mode
            self._zero_cold_water_status = internal_mode
            # 调用 API 下发零冷水模式命令
            if hasattr(self.coordinator, "api"):
                try:
                    await self.coordinator.api.async_set_zero_cold_water(self.device_id, internal_mode)
                except Exception as e:
                    _LOGGER.error("Failed to set zero cold water mode for %s: %s", self.device_id, e)
        else:
            for key, val in self._operation_mode_map.items():
                if val == operation_mode:
                    internal_mode = key
                    # 调用 API 设置普通模式
                    if hasattr(self.coordinator, "api"):
                        try:
                            await self.coordinator.api.async_set_operation_mode(self.device_id, internal_mode)
                        except Exception as e:
                            _LOGGER.error("Failed to set operation mode for %s: %s", self.device_id, e)
        if internal_mode:
            self.device_data["operation_mode"] = internal_mode
            self.async_write_ha_state()
        else:
            _LOGGER.warning("Unknown operation mode: %s", operation_mode)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {}
        status_info = self.device_data.get("statusInfo")
        if status_info:
            try:
                data = json.loads(status_info)
                events = data.get("events", [])
                for event in events:
                    if event.get("identifier") == "post":
                        output_data = event.get("outputData", {})
                        attrs.update({
                            "water_flow": float(output_data.get("waterFlow", 0)),
                            "in_water_temp": float(output_data.get("inWaterTemp", 0)),
                            "out_water_temp": float(output_data.get("outWaterTemp", 0)),
                            "fire_work_time": output_data.get("fireWorkTime"),
                            "total_water_num": output_data.get("totalWaterNum"),
                            "error_code": output_data.get("errorCode"),
                            "power_status": output_data.get("powerStatus"),
                            "device_status": output_data.get("deviceStatus"),
                            "zero_cold_water": self._zero_cold_water_status,
                        })
                        break
            except Exception:
                pass
        return attrs

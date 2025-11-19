"""Support for A.O. Smith water heaters with multi-language operation modes and zero cold water modes."""
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
from .api import AOSmithAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up A.O. Smith water heater entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    # operation mode map
    lang_code = getattr(hass.config, "language", "zh-Hans")
    config_json = getattr(coordinator, "config_json", {})
    operation_mode_map = config_json.get("entity", {}).get("water_heater", {}).get("operation_mode", {})

    entities = []
    for device_id, device_data in coordinator.data.items():
        if device_data.get("deviceCategory") == "19":  # Water heater
            entities.append(AOSmithWaterHeater(coordinator, device_id, operation_mode_map))

    _LOGGER.info("Setting up %d water heater entities", len(entities))
    async_add_entities(entities)


class AOSmithWaterHeater(AOSmithEntity, WaterHeaterEntity):
    """Representation of an A.O. Smith water heater with zero cold water modes."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = ["off", "heat"]

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

    @property
    def current_operation(self) -> str | None:
        """Return current operation: heat or off."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return "off"
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    power_status = output_data.get("powerStatus")
                    water_temp = output_data.get("waterTemp")
                    if power_status == "1" and water_temp and float(water_temp) > 0:
                        return "heat"
            return "off"
        except Exception:
            return "off"

    @property
    def operation_list(self) -> list[str]:
        """Return translated operation modes."""
        return [self._operation_mode_map.get(op, op) for op in self._attr_operation_list]

    @property
    def current_temperature(self) -> float | None:
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
        return self.device_data.get("target_temperature", self.current_temperature or 40.0)

    @property
    def min_temp(self) -> float:
        return 35.0

    @property
    def max_temp(self) -> float:
        return 70.0

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self.device_data["target_temperature"] = temperature
        self.async_write_ha_state()
        _LOGGER.info("Set target temperature for %s to %s", self.device_id, temperature)

        # 下发 API 命令
        api: AOSmithAPI = getattr(self.coordinator, "api", None)
        if api and api.is_authenticated:
            result = await api.async_send_command(
                device_id=self.device_id,
                service_identifier="WaterTempSet",
                input_data={"waterTemp": str(int(temperature))}
            )
            if result and result.get("status") == 200:
                _LOGGER.info("Temperature command sent successfully for %s", self.device_id)
            else:
                _LOGGER.warning("Failed to send temperature command for %s: %s", self.device_id, result)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        internal_mode = None
        for key, val in self._operation_mode_map.items():
            if val == operation_mode:
                internal_mode = key
                break
        if internal_mode is None:
            _LOGGER.warning("Unknown operation mode: %s", operation_mode)
            return

        self.device_data["operation_mode"] = internal_mode
        self.async_write_ha_state()
        _LOGGER.info("Set operation mode for %s to %s", self.device_id, internal_mode)

        # 下发 API 命令
        api: AOSmithAPI = getattr(self.coordinator, "api", None)
        if api and api.is_authenticated:
            result = await api.async_send_command(
                device_id=self.device_id,
                service_identifier="ModeSet",
                input_data={"mode": internal_mode}
            )
            if result and result.get("status") == 200:
                _LOGGER.info("Operation mode command sent successfully for %s", self.device_id)
            else:
                _LOGGER.warning("Failed to send operation mode command for %s: %s", self.device_id, result)

    async def async_set_zero_cold_water(self, mode: str) -> None:
        """Set zero cold water mode: 'one_key', 'half_pipe', or 'off'."""
        if mode not in ["one_key", "half_pipe", "off"]:
            _LOGGER.warning("Invalid zero cold water mode: %s", mode)
            return
        self._zero_cold_water_status = mode
        self.async_write_ha_state()
        _LOGGER.info("Set zero cold water mode for %s to %s", self.device_id, mode)

        # 下发 API 命令
        api: AOSmithAPI = getattr(self.coordinator, "api", None)
        if api and api.is_authenticated:
            service_map = {
                "one_key": "OneKeyZeroColdWater",
                "half_pipe": "HalfPipeZeroColdWater",
                "off": "CloseZeroColdWater"
            }
            service_identifier = service_map.get(mode)
            result = await api.async_send_command(
                device_id=self.device_id,
                service_identifier=service_identifier,
                input_data={}
            )
            if result and result.get("status") == 200:
                _LOGGER.info("Zero cold water command sent successfully for %s", self.device_id)
            else:
                _LOGGER.warning("Failed to send zero cold water command for %s: %s", self.device_id, result)

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

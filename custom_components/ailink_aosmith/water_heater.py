"""Support for A.O. Smith water heaters with multi-language operation modes."""
from __future__ import annotations

import json
import logging
import os
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

# JSON 文件目录
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "translations")

def load_config(hass, lang_code="zh-Hans"):
    """Load JSON configuration for current language."""
    file_path = os.path.join(CONFIG_DIR, f"{lang_code}.json")
    if not os.path.exists(file_path):
        _LOGGER.warning("Configuration file %s not found, fallback to zh-Hans.json", file_path)
        file_path = os.path.join(CONFIG_DIR, "zh-Hans.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up A.O. Smith water heater from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # 获取当前语言
    lang_code = getattr(hass.config, "language", "zh-Hans")
    config_json = load_config(hass, lang_code)
    operation_mode_map = config_json["entity"]["water_heater"].get("operation_mode", {})

    await coordinator.async_config_entry_first_refresh()

    entities = []
    for device_id, device_data in coordinator.data.items():
        if device_data.get("deviceCategory") == "19":  # Water heater
            entities.append(
                AOSmithWaterHeater(coordinator, device_id, operation_mode_map)
            )

    _LOGGER.info("Setting up %d water heater entities", len(entities))
    async_add_entities(entities)


class AOSmithWaterHeater(AOSmithEntity, WaterHeaterEntity):
    """Representation of an A.O. Smith water heater."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = ["off", "heat"]

    def __init__(self, coordinator, device_id, operation_mode_map: dict):
        """Initialize the water heater."""
        super().__init__(coordinator, device_id)
        self._attr_translation_key = "default_name"
        self._attr_name = self.device_data.get("productName", "A.O. Smith Water Heater")
        self._attr_icon = "mdi:water-boiler"
        self._attr_unique_id = f"{device_id}_water_heater"
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE |
            WaterHeaterEntityFeature.OPERATION_MODE
        )
        self._attr_precision = 1.0  # HomeKit precision

        # Multi-language operation mode
        self._operation_mode_map = operation_mode_map

    @property
    def current_operation(self) -> str | None:
        """Return current operation in internal key."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return "off"

        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    output_data = event.get("outputData", {})
                    water_temp = self._get_float_value(output_data, "waterTemp")
                    power_status = output_data.get("powerStatus")
                    if power_status == "1" and water_temp is not None and water_temp > 0:
                        return "heat"
            return "off"
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error parsing status info for %s: %s", self.device_id, e)
            return "off"

    @property
    def operation_list(self) -> list[str]:
        """Return translated operation modes for frontend display."""
        return [self._operation_mode_map.get(op, op) for op in self._attr_operation_list]

    @property
    def current_temperature(self) -> float | None:
        """Return the current water temperature."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None

        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    return self._get_float_value(event.get("outputData", {}), "waterTemp")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error getting current temperature for %s: %s", self.device_id, e)
        return 0.0

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return self.device_data.get("target_temperature", self.current_temperature or 40.0)

    @property
    def min_temp(self) -> float:
        return 35.0

    @property
    def max_temp(self) -> float:
        return 70.0

    def _get_float_value(self, data: dict, key: str) -> float | None:
        value = data.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            _LOGGER.debug("Cannot convert %s to float for key %s", value, key)
            return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            _LOGGER.info("Setting temperature for %s to %s", self.device_id, temperature)
            self.device_data["target_temperature"] = temperature
            self.async_write_ha_state()
            _LOGGER.warning("Temperature setting not yet implemented for device %s", self.device_id)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode using internal key."""
        internal_mode = None
        for key, val in self._operation_mode_map.items():
            if val == operation_mode:
                internal_mode = key
                break
        if internal_mode is None:
            _LOGGER.warning("Unknown operation mode: %s", operation_mode)
            return

        _LOGGER.info("Setting operation mode for %s to %s", self.device_id, internal_mode)
        self.device_data["operation_mode"] = internal_mode
        self.async_write_ha_state()
        _LOGGER.warning("Operation mode setting not yet implemented for device %s", self.device_id)

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
                            "water_flow": self._get_float_value(output_data, "waterFlow"),
                            "in_water_temp": self._get_float_value(output_data, "inWaterTemp"),
                            "out_water_temp": self._get_float_value(output_data, "outWaterTemp"),
                            "fire_work_time": output_data.get("fireWorkTime"),
                            "total_water_num": output_data.get("totalWaterNum"),
                            "error_code": output_data.get("errorCode"),
                            "power_status": output_data.get("powerStatus"),
                            "device_status": output_data.get("deviceStatus"),
                        })
                        break
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                _LOGGER.debug("Error parsing status info for attributes: %s", e)
        return attrs

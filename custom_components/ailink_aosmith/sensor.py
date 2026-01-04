"""Platform for Ai-Link A.O. Smith sensor integration with robust parsing, grouping, and value mapping."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLE_RAW_SENSORS,
    DEFAULT_ENABLE_RAW_SENSORS,
    DEVICE_CATEGORY_WATER_HEATER,
    DOMAIN,
)
from .entity import AOSmithEntity
from .translations import load_translation

_LOGGER = logging.getLogger(__name__)


def _extract_output_data(device_data: dict) -> dict:
    """Parse outputData from device status info."""
    if not device_data:
        return {}
    raw = device_data.get("statusInfo")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw if isinstance(raw, dict) else {}
    events = parsed.get("events", []) if isinstance(parsed, dict) else []
    for event in events:
        if event.get("identifier") == "post":
            return event.get("outputData", {}) or {}
    return {}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities
) -> None:
    """Set up sensors for Ai-Link A.O. Smith devices."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    cfg = load_translation(hass, config_entry)

    entity_sensors = cfg.get("entity", {}).get("sensor", {}) or {}
    sensor_mapping: Dict[str, Dict[str, Any]] = {}

    for key, info in entity_sensors.items():
        if isinstance(info, dict):
            name = info.get("name") or key
            group = info.get("group", "default")
            value_map = info.get("value_map", {})
            unit = info.get("unit")
            icon = info.get("icon")
        else:
            name = info
            group = "default"
            value_map = {}
            unit = None
            icon = None
        sensor_mapping[key] = {
            "name": name,
            "unit": unit,
            "icon": icon,
            "group": group,
            "value_map": value_map,
        }

    entities = []
    enable_raw_sensors = config_entry.options.get(
        CONF_ENABLE_RAW_SENSORS,
        DEFAULT_ENABLE_RAW_SENSORS,
    )

    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory", "")) != DEVICE_CATEGORY_WATER_HEATER:
            continue
        # Create mapped sensors
        for sensor_key in sensor_mapping.keys():
            entities.append(AOSmithSensor(coordinator, device_id, sensor_key, sensor_mapping))

        # Create raw sensors for extra keys not in mapping
        if enable_raw_sensors:
            output = _extract_output_data(device_data)
            if isinstance(output, dict):
                for key in output.keys():
                    if key not in sensor_mapping:
                        entities.append(AOSmithRawSensor(coordinator, device_id, key))

    _LOGGER.info("Setting up %d sensors for %s", len(entities), config_entry.entry_id)
    async_add_entities(entities, True)


class AOSmithSensor(AOSmithEntity, SensorEntity):
    """Mapped sensor entity via JSON with unit, icon, value_map."""

    def __init__(self, coordinator, device_id: str, sensor_key: str, mapping: dict):
        super().__init__(coordinator, device_id)
        self._sensor_key = sensor_key
        cfg = mapping.get(sensor_key, {})

        self._attr_name = cfg.get("name", sensor_key)
        self._attr_icon = cfg.get("icon")
        self._attr_unique_id = f"ailink_aosmith_{device_id}_{sensor_key}"
        self._attr_native_unit_of_measurement = cfg.get("unit")
        self._value_map = cfg.get("value_map", None)
        self._group = cfg.get("group", "default")

    @property
    def native_value(self):
        output = _extract_output_data(self.device_data)
        if not output:
            return None
        value = output.get(self._sensor_key)
        if value is None:
            return None
        if self._value_map and str(value) in self._value_map:
            return self._value_map[str(value)]
        if isinstance(value, str):
            val = value.strip()
            if val == "":
                return None
            if val.replace(".", "", 1).isdigit():
                return float(val) if "." in val else int(val)
        return value

    @property
    def extra_state_attributes(self):
        """Return all other outputData keys as extra attributes."""
        output = _extract_output_data(self.device_data)
        attrs = {}
        for k, v in output.items():
            if k != self._sensor_key:
                attrs[k] = v
        return attrs


class AOSmithRawSensor(AOSmithEntity, SensorEntity):
    """Dynamic sensor for unknown keys in outputData."""

    def __init__(self, coordinator, device_id: str, sensor_key: str):
        super().__init__(coordinator, device_id)
        self._sensor_key = sensor_key
        self._attr_name = sensor_key
        self._attr_unique_id = f"ailink_aosmith_raw_{device_id}_{sensor_key}"
        self._attr_icon = "mdi:information"
        self._attr_native_unit_of_measurement = None

    @property
    def native_value(self):
        output = _extract_output_data(self.device_data)
        return output.get(self._sensor_key)

    @property
    def extra_state_attributes(self):
        return {k: v for k, v in _extract_output_data(self.device_data).items() if k != self._sensor_key}

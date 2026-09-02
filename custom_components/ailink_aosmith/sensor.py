"""Platform for Ai-Link A.O. Smith sensor integration with robust parsing, grouping, and value mapping."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLE_RAW_SENSORS,
    DEFAULT_ENABLE_RAW_SENSORS,
    DEVICE_CATEGORY_WATER_HEATER,
    DOMAIN,
)
from .entity import AOSmithEntity, extract_output_data
from .translations import async_load_translation
from .protocol import numeric

_LOGGER = logging.getLogger(__name__)

MERGED_SENSOR_KEYS = {
    "powerStatus",
    "cruiseStatus",
    "pressurizeStatus",
    "halfPipeStatus",
    "halfPipeCirclelStatus",
}



async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities
) -> None:
    """Set up sensors for Ai-Link A.O. Smith devices."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    cfg = await async_load_translation(hass, config_entry)

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
        if not unit or (isinstance(unit, str) and unit.strip() == ""):
            unit = None

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
            if sensor_key in MERGED_SENSOR_KEYS:
                continue
            entities.append(AOSmithSensor(coordinator, device_id, sensor_key, sensor_mapping))

        # Keep legacy raw counters/history separate from normalized statistics.
        # The verified JSQ31-VJS energy protocol reports tenths of a cubic metre.
        if device_data.get("productModel") == "JSQ31-VJS":
            for key, name in (("totalGasNum", "史密斯累计燃气"),
                              ("cruisingTotalGasNum", "史密斯零冷水累计燃气")):
                entities.append(AOSmithGasSensor(coordinator, device_id, key, name))

        # Create raw sensors for extra keys not in mapping
        if enable_raw_sensors:
            output = extract_output_data(device_data)
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
        unit = cfg.get("unit")
        if not unit or (isinstance(unit, str) and unit.strip() == ""):
            unit = None
        self._attr_native_unit_of_measurement = unit
        self._value_map = cfg.get("value_map", None)
        self._group = cfg.get("group", "default")
        if self._value_map and unit is None:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(dict.fromkeys(self._value_map.values()))
        if unit == "°C":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if sensor_key == "waterFlow":
            self._attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
            self._attr_native_unit_of_measurement = "L/min"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if sensor_key in ("fanSpeed", "fanSpeedFeedback"):
            self._attr_native_unit_of_measurement = "rpm"
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        output = self._get_output_data()
        if not output:
            return None
        value = output.get(self._sensor_key)
        if value is None:
            return None
        if self._value_map:
            return self._value_map.get(str(value))
        if isinstance(value, str):
            val = value.strip()
            if val == "":
                return None
            if val.lstrip("-").replace(".", "", 1).isdigit():
                return float(val) if "." in val else int(val)
        return value

    @property
    def extra_state_attributes(self):
        """Return metadata for this mapped sensor."""
        return {
            "source_key": self._sensor_key,
            "group": self._group,
        }


class AOSmithGasSensor(AOSmithEntity, SensorEntity):
    """Normalized lifetime counter with a new identity for clean statistics."""

    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "m³"
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator, device_id, key, name):
        super().__init__(coordinator, device_id)
        self._sensor_key = key
        self._attr_name = name
        self._attr_unique_id = f"ailink_aosmith_{device_id}_{key}_m3"

    @property
    def native_value(self):
        value = numeric(self._get_output_data(), self._sensor_key)
        return None if value is None or value < 0 else round(value / 10, 1)

    @property
    def extra_state_attributes(self):
        return {"source_key": self._sensor_key, "raw_counter": numeric(
            self._get_output_data(), self._sensor_key), "counter_scale": 0.1}


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
        output = self._get_output_data()
        return output.get(self._sensor_key)

    @property
    def extra_state_attributes(self):
        return {"source_key": self._sensor_key}

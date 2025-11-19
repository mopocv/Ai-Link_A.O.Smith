"""Platform for Ai-Link A.O. Smith sensor integration with robust parsing and grouping."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)

TRANSLATIONS_DIRNAME = "translations"


def _translations_dir(hass: HomeAssistant) -> str:
    """Return path to translations directory, try hass.config.path then package-relative fallback."""
    # Preferred: custom_components/<domain>/translations under HA config
    try:
        path = hass.config.path("custom_components", DOMAIN, TRANSLATIONS_DIRNAME)
        if os.path.isdir(path):
            return path
    except Exception:
        pass

    # Fallback: directory next to this file
    return os.path.join(os.path.dirname(__file__), TRANSLATIONS_DIRNAME)


def load_config(hass: HomeAssistant, lang_code: str = "zh-Hans") -> dict:
    """Load the translation/config JSON for the given language.

    Returns the full parsed JSON (not only sensor_mapping).
    """
    translations_path = _translations_dir(hass)
    file_path = os.path.join(translations_path, f"{lang_code}.json")
    if not os.path.exists(file_path):
        _LOGGER.debug("Translation file for %s not found at %s, falling back to zh-Hans.json", lang_code, file_path)
        file_path = os.path.join(translations_path, "zh-Hans.json")

    if not os.path.exists(file_path):
        _LOGGER.warning("No translation file found at %s. Sensors will still try to work but without names/units.", file_path)
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        _LOGGER.exception("Failed to load translation JSON %s: %s", file_path, e)
        return {}


def _extract_output_data(device_data: dict) -> dict:
    """Extract outputData dict from device_data.statusInfo safely."""
    if not device_data:
        return {}
    raw = device_data.get("statusInfo")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        # statusInfo might already be a dict in some environments
        try:
            parsed = raw if isinstance(raw, dict) else {}
        except Exception:
            parsed = {}
    events = parsed.get("events", []) if isinstance(parsed, dict) else []
    for event in events:
        if event.get("identifier") == "post":
            return event.get("outputData", {}) or {}
    return {}


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
    """Set up sensors from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Ensure we have data
    await coordinator.async_config_entry_first_refresh()

    # load language JSON
    lang_code = getattr(hass.config, "language", "zh-Hans") or "zh-Hans"
    cfg = load_config(hass, lang_code)

    # Build mappings
    entity_sensors = cfg.get("entity", {}).get("sensor", {}) or {}
    unit_map = cfg.get("unit_of_measurement", {}) or {}
    icon_map = cfg.get("icon_mapping", {}) or {}

    sensor_mapping: Dict[str, Dict[str, Any]] = {}
    for key, info in entity_sensors.items():
        if isinstance(info, dict):
            name = info.get("name") or key
            group = info.get("group", "default")
        else:
            name = info
            group = "default"
        sensor_mapping[key] = {
            "name": name,
            "unit": unit_map.get(key),
            "icon": icon_map.get(key),
            "group": group,
        }

    entities = []
    for device_id, device_data in coordinator.data.items():
        # only water heater category (19)
        if str(device_data.get("deviceCategory", "")) != "19":
            continue

        # create static mapped sensors
        for sensor_key in sensor_mapping.keys():
            entities.append(AOSmithSensor(coordinator, device_id, sensor_key, sensor_mapping))

        # find dynamic fields from outputData and add raw sensors for unmapped ones
        output = _extract_output_data(device_data)
        if isinstance(output, dict):
            for key in output.keys():
                if key not in sensor_mapping:
                    # create a raw sensor per field (unique per field)
                    entities.append(AOSmithRawSensor(coordinator, device_id, key, sensor_mapping))

    _LOGGER.info("Setting up %d sensors for %s", len(entities), config_entry.entry_id)
    async_add_entities(entities, True)


class AOSmithSensor(AOSmithEntity, SensorEntity):
    """Sensor entity mapped via JSON config (static mapping)."""

    def __init__(self, coordinator, device_id: str, sensor_key: str, mapping: dict):
        super().__init__(coordinator, device_id)
        self._sensor_key = sensor_key
        cfg = mapping.get(sensor_key, {})

        # name/icon/unique id
        self._attr_name = cfg.get("name", sensor_key)
        self._attr_icon = cfg.get("icon")
        self._attr_unique_id = f"ailink_aosmith_{device_id}_{sensor_key}"

        # IMPORTANT: use native unit
        unit = cfg.get("unit")
        if unit:
            self._attr_native_unit_of_measurement = unit

        self._group = cfg.get("group", "default")

    @property
    def native_value(self):
        """Return sensor value from device outputData."""
        output = _extract_output_data(self.device_data)
        if not output:
            return None
        value = output.get(self._sensor_key)
        if value is None:
            return None

        # try numeric conversion
        if isinstance(value, str):
            val = value.strip()
            if val == "":
                return None
            # handle ints and floats like "0", "0.0"
            if val.replace(".", "", 1).isdigit():
                return float(val) if "." in val else int(val)
        # already numeric
        return value


class AOSmithRawSensor(AOSmithEntity, SensorEntity):
    """Dynamic sensor for a specific raw outputData key."""

    def __init__(self, coordinator, device_id: str, field_key: str, mapping: dict):
        super().__init__(coordinator, device_id)
        self._field_key = field_key
        # Use translation if available: mapping may have a human name for the same field
        human = mapping.get(field_key, {}).get("name") if mapping else None
        product = self.device_data.get("productName") or "A.O. Smith"
        self._attr_name = f"{product} {human or field_key}"
        self._attr_unique_id = f"ailink_aosmith_{device_id}_raw_{field_key}"
        self._attr_icon = mapping.get(field_key, {}).get("icon") if mapping else "mdi:information-outline"
        # try unit if mapping supplies it (usually not)
        unit = mapping.get(field_key, {}).get("unit") if mapping else None
        if unit:
            self._attr_native_unit_of_measurement = unit
        self._group = mapping.get(field_key, {}).get("group", "dynamic") if mapping else "dynamic"

    @property
    def native_value(self):
        output = _extract_output_data(self.device_data)
        if not output:
            return None
        value = output.get(self._field_key)
        if value is None:
            return None
        if isinstance(value, str):
            val = value.strip()
            if val == "":
                return None
            if val.replace(".", "", 1).isdigit():
                return float(val) if "." in val else int(val)
        return value

    @property
    def extra_state_attributes(self):
        """Expose group and raw-debug fields for the dynamic sensor."""
        attrs = {"group": self._group}
        # include the entire outputData (useful for debugging)
        try:
            attrs["outputData"] = _extract_output_data(self.device_data)
        except Exception:
            attrs["outputData"] = {}
        return attrs

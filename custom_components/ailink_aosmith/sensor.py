"""Platform for Ai-Link A.O. Smith sensor integration with dynamic mapping and grouping."""
import logging
import json
import os
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "translations")

def load_config(hass, lang_code="zh-Hans"):
    """Load JSON config file according to Home Assistant language."""
    file_path = os.path.join(CONFIG_DIR, f"{lang_code}.json")
    if not os.path.exists(file_path):
        _LOGGER.warning("Configuration file %s not found, fallback to zh-Hans.json", file_path)
        file_path = os.path.join(CONFIG_DIR, "zh-Hans.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Ai-Link A.O. Smith sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    lang_code = getattr(hass.config, "language", "zh-Hans")
    config = load_config(hass, lang_code)

    ENTITY_NAMES = config.get("entity", {}).get("sensor", {})
    UNIT_MAPPING = config.get("unit_of_measurement", {})
    ICON_MAPPING = config.get("icon_mapping", {})

    SENSOR_TYPES = {}
    for key, info in ENTITY_NAMES.items():
        SENSOR_TYPES[key] = {
            "name": info.get("name") if isinstance(info, dict) else info,
            "unit": UNIT_MAPPING.get(key),
            "icon": ICON_MAPPING.get(key),
            "group": info.get("group") if isinstance(info, dict) else "default"
        }

    await coordinator.async_config_entry_first_refresh()

    entities = []
    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory")) != "19":  # 水暖类设备
            continue

        # 动态 outputData
        output_keys = set()
        status_info = device_data.get("statusInfo")
        if status_info:
            try:
                parsed = json.loads(status_info)
                events = parsed.get("events", [])
                for event in events:
                    if event.get("identifier") == "post":
                        output_keys.update(event.get("outputData", {}).keys())
                        break
            except Exception as e:
                _LOGGER.warning("Failed to parse statusInfo: %s", e)

        # JSON 定义的传感器
        for sensor_key in SENSOR_TYPES:
            entities.append(AOSmithSensor(coordinator, device_id, sensor_key, SENSOR_TYPES))

        # 动态未映射的传感器
        mapped_keys = set(ENTITY_NAMES.keys())
        for key in output_keys:
            if key not in mapped_keys:
                entities.append(AOSmithRawSensor(coordinator, device_id, key))

    _LOGGER.info("Setting up %d sensor entities", len(entities))
    async_add_entities(entities, True)


class AOSmithSensor(AOSmithEntity, SensorEntity):
    """Ai-Link sensor entity with JSON mapping and group."""

    def __init__(self, coordinator, device_id, sensor_key, sensor_types):
        super().__init__(coordinator, device_id)
        self._sensor_key = sensor_key
        cfg = sensor_types.get(sensor_key, {})

        self._attr_name = cfg.get("name", sensor_key)
        self._attr_unique_id = f"ailink_aosmith_{sensor_key}_{device_id}"
        self._attr_unit_of_measurement = cfg.get("unit")
        self._attr_icon = cfg.get("icon")
        self._group = cfg.get("group", "default")

    @property
    def native_value(self):
        return self._get_sensor_value()

    def _get_sensor_value(self):
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
        try:
            data = json.loads(status_info)
            events = data.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    value = event.get("outputData", {}).get(self._sensor_key)
                    if value is None:
                        return None
                    if isinstance(value, str) and value.replace(".", "", 1).isdigit():
                        return float(value) if "." in value else int(value)
                    return value
        except Exception as e:
            _LOGGER.debug("Error parsing sensor %s: %s", self._sensor_key, e)
        return None

    @property
    def extra_state_attributes(self):
        """Expose group for UI display."""
        return {"group": self._group}


class AOSmithRawSensor(AOSmithEntity, SensorEntity):
    """Dynamic sensor not defined in JSON mapping."""

    def __init__(self, coordinator, device_id, field_key):
        super().__init__(coordinator, device_id)
        self._field_key = field_key
        product_name = self.device_data.get("productName") or "A.O. Smith"
        self._attr_name = f"{product_name} {field_key}"
        self._attr_unique_id = f"ailink_aosmith_{field_key}_{device_id}"
        self._attr_icon = "mdi:information-outline"
        self._group = "dynamic"

    @property
    def native_value(self):
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
        try:
            parsed = json.loads(status_info)
            events = parsed.get("events", [])
            for event in events:
                if event.get("identifier") == "post":
                    value = event.get("outputData", {}).get(self._field_key)
                    if value is None:
                        return None
                    if isinstance(value, str) and value.replace(".", "", 1).isdigit():
                        return float(value) if "." in value else int(value)
                    return value
        except Exception as e:
            _LOGGER.debug("Error parsing raw sensor %s: %s", self._field_key, e)
        return None

    @property
    def extra_state_attributes(self):
        return {"group": self._group}

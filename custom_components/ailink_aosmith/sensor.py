"""Sensors for Ai-Link A.O. Smith."""
import json
import logging
import os
from homeassistant.components.sensor import SensorEntity

from .entity import AOSmithEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TRANSLATION_DIR = "translations"


# ------------------------------------------------------------
# 加载翻译 JSON（传感器定义）
# ------------------------------------------------------------
def load_config(hass, lang):
    file_path = os.path.join(
        hass.config.path("custom_components", DOMAIN, TRANSLATION_DIR),
        f"{lang}.json",
    )

    if not os.path.exists(file_path):
        _LOGGER.warning("Translation file missing: %s", file_path)
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("sensor_mapping", {})
    except Exception as e:
        _LOGGER.error("Error loading translation JSON: %s", e)
        return {}


# ------------------------------------------------------------
# 平台初始化
# ------------------------------------------------------------
async def async_setup_entry(hass, entry, async_add_entities):
    lang = hass.config.language
    mapping = load_config(hass, lang)

    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id, _dev in coordinator.data.items():
        # 静态映射字段
        for key in mapping.keys():
            entities.append(AOSmithSensor(coordinator, device_id, key, mapping))

        # 补充：添加所有动态字段
        entities.append(AOSmithRawSensor(coordinator, device_id))

    async_add_entities(entities)


# ------------------------------------------------------------
# 工具：解析 statusInfo → outputData
# ------------------------------------------------------------
def extract_output_data(device_data):
    """Return dict of outputData from statusInfo."""
    try:
        raw = device_data.get("statusInfo")
        if not raw:
            return {}

        status = json.loads(raw)
        events = status.get("events", [])
        for ev in events:
            if ev.get("identifier") == "post":
                return ev.get("outputData", {})

        return {}
    except Exception:
        return {}


# ------------------------------------------------------------
# 静态传感器（mapping 定义的）
# ------------------------------------------------------------
class AOSmithSensor(AOSmithEntity, SensorEntity):
    """Sensor mapped via JSON config."""

    def __init__(self, coordinator, device_id, key, mapping):
        super().__init__(coordinator, device_id)
        self._key = key
        cfg = mapping.get(key, {})

        self._attr_name = cfg.get("name", key)
        self._attr_icon = cfg.get("icon")
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"
        self._attr_native_unit_of_measurement = cfg.get("unit")

        self._group = cfg.get("group", "other")

    @property
    def native_value(self):
        """Return value from outputData."""
        output = extract_output_data(self.device_data)
        return output.get(self._key)


# ------------------------------------------------------------
# 动态传感器（未映射字段）
# ------------------------------------------------------------
class AOSmithRawSensor(AOSmithEntity, SensorEntity):
    """Expose unmapped outputData fields."""

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self._attr_name = f"Raw Sensors {device_id}"
        self._attr_unique_id = f"{DOMAIN}_{device_id}_raw"

    @property
    def extra_state_attributes(self):
        """Return raw outputData for debugging."""
        return extract_output_data(self.device_data)

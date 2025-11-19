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
# 加载多语言 JSON 配置
# ------------------------------------------------------------
def load_config(hass, lang):
    """
    Load sensor mapping rules from translations/<lang>.json
    Example: zh-Hans.json / en.json
    """
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
    for device_id, device in coordinator.data.items():
        # 静态映射传感器
        for key in mapping.keys():
            entities.append(AOSmithSensor(coordinator, device_id, key, mapping))

        # 动态原始传感器（statusInfo 里面出来的）
        entities.append(AOSmithRawSensor(coordinator, device_id))

    async_add_entities(entities)


# ------------------------------------------------------------
# 静态映射传感器
# ------------------------------------------------------------
class AOSmithSensor(AOSmithEntity, SensorEntity):
    """Sensor mapped via JSON config."""

    def __init__(self, coordinator, device_id, key, mapping):
        super().__init__(coordinator, device_id)
        self._key = key
        cfg = mapping.get(key, {})

        # 名称/图标
        self._attr_name = cfg.get("name", key)
        self._attr_icon = cfg.get("icon")
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"

        # 🔥 正确：HA 2024+ 使用 native_unit_of_measurement
        self._attr_native_unit_of_measurement = cfg.get("unit")

        # 分组
        self._group = cfg.get("group", "other")

    @property
    def native_value(self):
        """Return mapped value from device data."""
        data = self.device_data
        return data.get(self._key)


# ------------------------------------------------------------
# 动态传感器（所有未映射的字段）
# ------------------------------------------------------------
class AOSmithRawSensor(AOSmithEntity, SensorEntity):
    """Expose dynamic raw fields from Ai-Link device."""

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self._prefix = "raw_"
        self._attr_name = f"Raw Sensors {device_id}"
        self._attr_unique_id = f"{DOMAIN}_{device_id}_raw"

    @property
    def extra_state_attributes(self):
        """Return all raw fields except those already mapped."""
        raw = {}
        data = self.device_data or {}

        # 自带字段不暴露
        blacklist = {
            "productName",
            "productModel",
            "statusInfo",
            "deviceId",
        }

        for k, v in data.items():
            if k not in blacklist:
                raw[k] = v

        return raw

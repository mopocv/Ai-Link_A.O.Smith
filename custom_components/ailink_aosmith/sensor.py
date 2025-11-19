"""Platform for Ai-Link A.O. Smith sensor integration with dynamic mapping from JSON config."""
import logging
import json
import os
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfVolume
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)

# JSON 文件目录
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "translations")

def load_config(hass, lang_code="zh-Hans"):
    """根据语言加载 JSON 配置文件."""
    file_path = os.path.join(CONFIG_DIR, f"{lang_code}.json")
    if not os.path.exists(file_path):
        _LOGGER.warning("Configuration file %s not found, fallback to zh-Hans.json", file_path)
        file_path = os.path.join(CONFIG_DIR, "zh-Hans.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Ai-Link A.O. Smith sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # 获取当前 Home Assistant 语言
    lang_code = getattr(hass.config, "language", "zh-Hans")
    config = load_config(hass, lang_code)

    # 从配置生成映射
    ENTITY_NAMES = config.get("entity", {}).get("sensor", {})
    UNIT_MAPPING = config.get("unit_of_measurement", {})
    ICON_MAPPING = config.get("icon_mapping", {})

    SENSOR_TYPES = {}
    for sensor_key, sensor_name in ENTITY_NAMES.items():
        SENSOR_TYPES[sensor_key] = {
            "name": sensor_name,
            "unit": UNIT_MAPPING.get(sensor_key),
            "icon": ICON_MAPPING.get(sensor_key)
        }

    # Wait for initial data to be loaded
    await coordinator.async_config_entry_first_refresh()

    entities = []
    for device_id, device_data in coordinator.data.items():
        category = device_data.get("deviceCategory")
        if str(category) != "19":  # 只处理水暖类设备
            continue

        # 动态获取 outputData 字段
        output_keys = set()
        status_info = device_data.get("statusInfo")
        if status_info:
            try:
                parsed = json.loads(status_info)
                events = parsed.get("events", [])
                for event in events:
                    if event.get("identifier") == "post":
                        output_data = event.get("outputData", {})
                        output_keys.update(output_data.keys())
                        break
            except Exception as e:
                _LOGGER.warning("Failed to parse statusInfo: %s", e)

        # 创建配置 JSON 中定义的传感器
        for sensor_key in SENSOR_TYPES:
            entities.append(AOSmithSensor(coordinator, device_id, sensor_key, SENSOR_TYPES))

        # 创建动态 outputData 未映射的传感器
        mapped_keys = set(ENTITY_NAMES.keys())
        for key in output_keys:
            if key not in mapped_keys:
                entities.append(AOSmithRawSensor(coordinator, device_id, key))

    _LOGGER.info("Setting up %d sensor entities", len(entities))
    async_add_entities(entities, True)


class AOSmithSensor(AOSmithEntity, SensorEntity):
    """Representation of an Ai-Link A.O. Smith sensor from JSON mapping."""

    def __init__(self, coordinator, device_id, sensor_key, sensor_types):
        super().__init__(coordinator, device_id)
        self._sensor_key = sensor_key
        self._device_id = device_id

        cfg = sensor_types.get(sensor_key, {})
        self._attr_name = cfg.get("name", f"{sensor_key}")
        self._attr_unique_id = f"ailink_aosmith_{sensor_key}_{device_id}"
        self._attr_unit_of_measurement = cfg.get("unit")
        self._attr_icon = cfg.get("icon")
        self._attr_translation_key = sensor_key

        # HomeKit compatibility
        if sensor_key in ["waterTemp", "inWaterTemp", "outWaterTemp", "cOConcentration"]:
            self._attr_state_class = "measurement"

    @property
    def native_value(self):
        """Return the sensor value from device data."""
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
                    output_data = event.get("outputData", {})
                    value = output_data.get(self._sensor_key)
                    if value is None:
                        return None
                    try:
                        if isinstance(value, str) and value.isdigit():
                            return int(value)
                        return float(value)
                    except Exception:
                        return value
        except Exception as e:
            _LOGGER.debug("Error parsing sensor %s: %s", self._sensor_key, e)
        return None


class AOSmithRawSensor(AOSmithEntity, SensorEntity):
    """Representation of dynamic/outputData sensor not defined in JSON."""

    def __init__(self, coordinator, device_id, field_key: str):
        super().__init__(coordinator, device_id)
        self._field_key = field_key
        product_name = self.device_data.get("productName") or "A.O. Smith"
        self._attr_name = f"{product_name} {field_key}"
        self._attr_unique_id = f"ailink_aosmith_{field_key}_{device_id}"
        self._attr_icon = "mdi:information-outline"

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
                    output_data = event.get("outputData", {})
                    value = output_data.get(self._field_key)
                    if value is None:
                        return None
                    try:
                        if isinstance(value, str) and value.isdigit():
                            return int(value)
                        return float(value)
                    except Exception:
                        return value
        except Exception as e:
            _LOGGER.debug("Error parsing raw sensor %s: %s", self._field_key, e)
        return None

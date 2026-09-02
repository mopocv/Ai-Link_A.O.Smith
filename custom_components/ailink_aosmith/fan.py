"""Three-speed pressure booster, represented by HomeKit's native fan control."""
import math
from homeassistant.components.fan import FanEntity, FanEntityFeature
from .const import DOMAIN, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity
from .protocol import flag, numeric


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for key, data in coordinator.data.items():
        if str(data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            entities.extend((AOSmithBooster(coordinator, key), AOSmithDurationSlider(coordinator, key)))
    async_add_entities(entities)


class AOSmithBooster(AOSmithEntity, FanEntity):
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    _attr_speed_count = 3
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self._attr_name = f"{self.device_data.get('productName', 'Water Heater')} 三档增压"
        self._attr_unique_id = f"{device_id}_booster"

    @property
    def is_on(self):
        return flag(self._get_output_data(), "pressurize")

    @property
    def percentage_step(self):
        """Expose one slider; actual writes still snap to the three pump levels."""
        return 1

    @property
    def percentage(self):
        if self.is_on is False:
            return 0
        level = numeric(self._get_output_data(), "pressurizeLevel")
        return None if level not in (1, 2, 3) or self.is_on is None else round(level * 100 / 3)

    @property
    def extra_state_attributes(self):
        return {"pressure_level": numeric(self._get_output_data(), "pressurizeLevel")}

    async def async_set_percentage(self, percentage):
        percentage = float(percentage)
        if not math.isfinite(percentage) or not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        if percentage == 0:
            await self.async_turn_off()
            return
        # HA/HomeKit represent the three discrete speeds as 33/67/100 percent.
        level = max(1, min(3, round(percentage * 3 / 100)))
        await self.coordinator.async_command(self.device_id, "SetPressurizeLevel", {"pressurizeLevel": str(level)}, {"pressurizeLevel": level})
        if not self.is_on:
            await self.async_turn_on()

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        await self.coordinator.async_command(self.device_id, "PressurizeOnOff", {"pressurize": "1"}, {"pressurize": 1})

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_command(self.device_id, "PressurizeOnOff", {"pressurize": "0"}, {"pressurize": 0})


class AOSmithDurationSlider(AOSmithEntity, FanEntity):
    """HomeKit percentage adapter: one percent means one minute, not fan speed.

    HomeKit has no standalone number accessory. This optional adapter edits only
    duration; it never starts circulation. Endpoints clamp to the device's range.
    """

    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    _attr_speed_count = 100
    _attr_icon = "mdi:timer-cog"

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self._attr_name = "零冷水时长（1%=1分钟）"
        self._attr_unique_id = f"{device_id}_duration_slider"

    @property
    def percentage(self):
        value = numeric(self._get_output_data(), "curiesTime")
        return value if value is not None and 1 <= value <= 99 else None

    @property
    def is_on(self):
        return None if self.percentage is None else True

    @property
    def extra_state_attributes(self):
        return {"duration_minutes": self.percentage, "minimum_minutes": 1, "maximum_minutes": 99}

    async def async_set_percentage(self, percentage):
        value = float(percentage)
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        minutes = max(1, min(99, math.floor(value + 0.5)))
        await self.coordinator.async_command(self.device_id, "WaterCruiseTimer",
            {"WaterCruiseTimer": str(minutes)}, {"curiesTime": minutes})

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is not None:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs):
        # HomeKit sends Active=0 at the bottom of a fan slider. Duration cannot
        # be disabled, so this selects the minimum without touching cruiseStatus.
        await self.async_set_percentage(0)

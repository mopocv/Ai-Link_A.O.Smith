"""Three-speed pressure booster, represented by HomeKit's native fan control."""
import math
from homeassistant.components.fan import FanEntity, FanEntityFeature
from .const import DOMAIN, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity
from .protocol import flag, numeric


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AOSmithBooster(coordinator, key) for key, data in coordinator.data.items()
                       if str(data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER)


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

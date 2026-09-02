"""Device modes and HomeKit-compatible duration preset switches."""
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity
from .protocol import flag, numeric, DURATION_PRESETS

# key, display name, command, input field, reported field
MODES = (
    ("cruise", "零冷水", "WaterCruiseOnOff", "cruiseStatus", "cruiseStatus"),
    ("half_pipe", "节能半管零冷水", "setHalfPipeCircle", "setHalfPipeCircle", "halfPipeCirclelStatus"),
    ("pressurize", "增压", "PressurizeOnOff", "pressurize", "pressurize"),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for key, data in coordinator.data.items():
        if str(data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            entities.extend(AOSmithModeSwitch(coordinator, key, mode) for mode in MODES)
            entities.extend(AOSmithDurationPreset(coordinator, key, minutes) for minutes in DURATION_PRESETS)
    async_add_entities(entities)


class AOSmithModeSwitch(AOSmithEntity, SwitchEntity):
    def __init__(self, coordinator, device_id, mode):
        super().__init__(coordinator, device_id)
        key, name, self._command, self._input, self._reported = mode
        self._attr_name = f"{self.device_data.get('productName', 'Water Heater')} {name}"
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_icon = "mdi:water-pump" if key == "pressurize" else "mdi:water-sync"

    @property
    def is_on(self):
        return flag(self._get_output_data(), self._reported)

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_command(self.device_id, self._command, {self._input: "1"}, {self._reported: 1})

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_command(self.device_id, self._command, {self._input: "0"}, {self._reported: 0})


class AOSmithDurationPreset(AOSmithEntity, SwitchEntity):
    """A preset changes duration only; it does not start recirculation."""
    _attr_icon = "mdi:timer-cog"

    def __init__(self, coordinator, device_id, minutes):
        super().__init__(coordinator, device_id)
        self._minutes = minutes
        self._attr_name = f"零冷水时长 {minutes} 分钟"
        self._attr_unique_id = f"{device_id}_duration_{minutes}"

    @property
    def is_on(self):
        value = numeric(self._get_output_data(), "curiesTime")
        return None if value is None else value == self._minutes

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_command(self.device_id, "WaterCruiseTimer", {"WaterCruiseTimer": str(self._minutes)}, {"curiesTime": self._minutes})

    async def async_turn_off(self, **kwargs):
        # A duration cannot be unset. Re-publish the actual selected preset.
        self.async_write_ha_state()

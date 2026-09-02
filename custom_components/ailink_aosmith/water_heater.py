"""Native water heater entity, sharing validated controls with the thermostat."""
from homeassistant.components.water_heater import WaterHeaterEntity, WaterHeaterEntityFeature, STATE_GAS
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, UnitOfTemperature
from .const import DOMAIN, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity
from .protocol import numeric, flag, temperature_limits


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AOSmithWaterHeater(coordinator, key) for key, data in coordinator.data.items()
                       if str(data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER)


class AOSmithWaterHeater(AOSmithEntity, WaterHeaterEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (WaterHeaterEntityFeature.TARGET_TEMPERATURE
                               | WaterHeaterEntityFeature.ON_OFF | WaterHeaterEntityFeature.OPERATION_MODE)
    _attr_operation_list = [STATE_OFF, STATE_GAS]
    _attr_precision = 1.0

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self._attr_name = self.device_data.get("productName", "A.O. Smith Water Heater")
        self._attr_unique_id = f"{device_id}_water_heater"

    @property
    def current_operation(self):
        value = flag(self._get_output_data(), "powerStatus", "powerOn")
        return None if value is None else STATE_GAS if value else STATE_OFF

    @property
    def is_on(self):
        return flag(self._get_output_data(), "powerStatus", "powerOn")

    @property
    def current_temperature(self):
        return numeric(self._get_output_data(), "outWaterTemp")

    @property
    def target_temperature(self):
        return numeric(self._get_output_data(), "waterTemp", "setTemp")

    @property
    def min_temp(self):
        return temperature_limits(self._get_output_data())[0]

    @property
    def max_temp(self):
        return temperature_limits(self._get_output_data())[1]

    async def async_set_temperature(self, **kwargs):
        value = kwargs[ATTR_TEMPERATURE]
        await self.coordinator.async_command(self.device_id, "temperature", {"temperature": value}, {"waterTemp": value})

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_command(self.device_id, "SetDeviceOnOff", {"powerStatus": "1"}, {"powerStatus": 1})

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_command(self.device_id, "SetDeviceOnOff", {"powerStatus": "0"}, {"powerStatus": 0})

    async def async_set_operation_mode(self, operation_mode):
        if operation_mode == STATE_GAS:
            await self.async_turn_on()
        elif operation_mode == STATE_OFF:
            await self.async_turn_off()
        else:
            raise ValueError(f"Unsupported operation mode: {operation_mode}")

    @property
    def extra_state_attributes(self):
        output = self._get_output_data()
        return {key: output[key] for key in ("waterFlow", "fanSpeed", "outWaterTemp", "heating", "powerStatus", "cruiseStatus", "halfPipeCirclelStatus", "pressurize", "pressurizeLevel", "curiesTime") if key in output}

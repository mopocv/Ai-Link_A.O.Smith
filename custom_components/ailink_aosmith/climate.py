"""HomeKit-compatible thermostat for the gas water heater."""
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode, HVACAction
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from .const import DOMAIN, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity
from .protocol import numeric, flag, temperature_limits


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AOSmithClimate(coordinator, key) for key, data in coordinator.data.items()
                       if str(data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER)


class AOSmithClimate(AOSmithEntity, ClimateEntity):
    """Expose target/outlet temperature and actual burner activity separately."""
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (ClimateEntityFeature.TARGET_TEMPERATURE
                               | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF)
    _attr_icon = "mdi:water-boiler"

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self._attr_name = f"{self.device_data.get('productName', 'Water Heater')} 温控"
        self._attr_unique_id = f"{device_id}_climate"

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

    @property
    def target_temperature_step(self):
        return temperature_limits(self._get_output_data())[2]

    @property
    def hvac_mode(self):
        on = flag(self._get_output_data(), "powerStatus", "powerOn")
        return None if on is None else HVACMode.HEAT if on else HVACMode.OFF

    @property
    def hvac_action(self):
        if self.hvac_mode is None:
            return None
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        heating = flag(self._get_output_data(), "heating")
        return None if heating is None else HVACAction.HEATING if heating else HVACAction.IDLE

    async def async_set_temperature(self, **kwargs):
        value = kwargs[ATTR_TEMPERATURE]
        await self.coordinator.async_command(self.device_id, "temperature", {"temperature": value}, {"waterTemp": value})

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode not in self.hvac_modes:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")
        value = "1" if hvac_mode == HVACMode.HEAT else "0"
        await self.coordinator.async_command(self.device_id, "SetDeviceOnOff", {"powerStatus": value}, {"powerStatus": value})

    async def async_turn_on(self):
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)

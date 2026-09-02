"""Runtime tests, using Home Assistant when installed."""
import asyncio
import copy
import importlib.util
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

HAS_HA = importlib.util.find_spec('homeassistant') is not None
if HAS_HA:
    from custom_components.ailink_aosmith import AOSmithDataUpdateCoordinator
    from custom_components.ailink_aosmith.api import AOSmithAPI
    from custom_components.ailink_aosmith.climate import AOSmithClimate
    from custom_components.ailink_aosmith.fan import AOSmithBooster, AOSmithDurationSlider
    from custom_components.ailink_aosmith.sensor import AOSmithGasSensor
    from custom_components.ailink_aosmith.number import AOSmithCuriesTimeNumber
    from homeassistant.exceptions import HomeAssistantError


def status(**values):
    return {'productModel': 'JSQ31-VJS', 'devState': 1,
            'appDeviceStatusInfoEntity': {'statusInfo': {'events': [
                {'identifier': 'post', 'outputData': {'waterTemp': '38', 'outWaterTemp': '26',
                 'powerStatus': '1', 'heating': 0, 'pressurize': '1', 'pressurizeLevel': '3', **values}}]}}}


@unittest.skipUnless(HAS_HA, 'Home Assistant runtime required')
class ControlTests(unittest.IsolatedAsyncioTestCase):
    def coordinator(self):
        c = object.__new__(AOSmithDataUpdateCoordinator)
        c._command_lock = asyncio.Lock()
        c.api = SimpleNamespace(async_get_device_status=AsyncMock(return_value=status()), async_send_command=AsyncMock(return_value={'status': 200}))
        c.data = {'test': status()}
        c.async_set_updated_data = lambda data: setattr(c, 'data', data)
        return c

    async def test_confirmed_command_updates_reported_state(self):
        c = self.coordinator()
        c.api.async_get_device_status.side_effect = [status(), status(waterTemp='39')]
        with patch('custom_components.ailink_aosmith.asyncio.sleep', new=AsyncMock()):
            await c.async_command('test', 'temperature', {'temperature': 39}, {'waterTemp': 39})
        c.api.async_send_command.assert_awaited_once_with('test', 'WaterTempSet', {'waterTemp': '39'}, device_type='JSQ31-VJS')

    async def test_cloud_rejection_propagates(self):
        c = self.coordinator()
        c.api.async_send_command.side_effect = ValueError('rejected')
        with self.assertRaises(HomeAssistantError):
            await c.async_command('test', 'WaterCruiseTimer', {'WaterCruiseTimer': '5'}, {'curiesTime': 5})

    async def test_unconfirmed_write_is_not_success(self):
        c = self.coordinator()
        original = copy.deepcopy(c.data)
        with patch('custom_components.ailink_aosmith.asyncio.sleep', new=AsyncMock()):
            with self.assertRaises(HomeAssistantError):
                await c.async_command('test', 'temperature', {'temperature': 39}, {'waterTemp': 39})
        self.assertEqual(c.data['test']['appDeviceStatusInfoEntity'], original['test']['appDeviceStatusInfoEntity'])

    async def test_offline_device_never_receives_command(self):
        c = self.coordinator()
        c.api.async_get_device_status.return_value = None
        with self.assertRaises(HomeAssistantError):
            await c.async_command('test', 'temperature', {'temperature': 39}, {'waterTemp': 39})
        c.api.async_send_command.assert_not_awaited()

    async def test_entities_show_separate_target_and_outlet(self):
        c = SimpleNamespace(data={'test': status()}, config_entry=None, async_command=AsyncMock())
        climate = AOSmithClimate(c, 'test')
        self.assertEqual(climate.target_temperature, 38)
        self.assertEqual(climate.current_temperature, 26)
        self.assertEqual(climate.hvac_mode, 'heat')
        self.assertEqual(climate.hvac_action, 'idle')
        await climate.async_set_temperature(temperature=38.5)
        c.async_command.assert_awaited_with('test', 'temperature', {'temperature': 39}, {'waterTemp': 39})
        fan = AOSmithBooster(c, 'test')
        self.assertEqual(fan.speed_count, 3)
        self.assertEqual(fan.percentage_step, 1)
        for percentage, level in ((33, 1), (67, 2), (100, 3)):
            await fan.async_set_percentage(percentage)
            c.async_command.assert_awaited_with('test', 'SetPressurizeLevel', {'pressurizeLevel': str(level)}, {'pressurizeLevel': level})
        number = AOSmithCuriesTimeNumber(c, 'test')
        self.assertIsNone(number.native_value)
        await number.async_set_native_value(99)
        c.async_command.assert_awaited_with('test', 'WaterCruiseTimer', {'WaterCruiseTimer': '99'}, {'curiesTime': 99})

    async def test_duration_slider_endpoints_and_single_minute_steps(self):
        c = SimpleNamespace(data={'test': status(curiesTime='5')}, config_entry=None, async_command=AsyncMock())
        slider = AOSmithDurationSlider(c, 'test')
        self.assertEqual(slider.percentage_step, 1)
        self.assertEqual(slider.percentage, 5)
        for percent, minutes in ((0, 1), (1, 1), (6, 6), (7, 7), (99, 99), (100, 99)):
            await slider.async_set_percentage(percent)
            c.async_command.assert_awaited_with('test', 'WaterCruiseTimer', {'WaterCruiseTimer': str(minutes)}, {'curiesTime': minutes})
        for value in (-1, 101, float('nan')):
            with self.assertRaises(ValueError):
                await slider.async_set_percentage(value)

    async def test_gas_units_and_missing_counters(self):
        c = SimpleNamespace(data={'test': status(totalGasNum='2549')}, config_entry=None)
        sensor = AOSmithGasSensor(c, 'test', 'totalGasNum', 'Gas')
        self.assertEqual(sensor.native_value, 254.9)
        self.assertEqual(sensor.native_unit_of_measurement, 'm³')
        self.assertEqual(sensor.state_class, 'total_increasing')
        self.assertEqual(sensor.device_class, 'gas')
        for value in (None, '', 'bad', '-1', 'nan'):
            c.data = {'test': status(totalGasNum=value)}
            self.assertIsNone(sensor.native_value)

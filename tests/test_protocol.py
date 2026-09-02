"""Protocol regressions; run without a Home Assistant installation."""
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("protocol", Path(__file__).parents[1] / "custom_components/ailink_aosmith/protocol.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProtocolTests(unittest.TestCase):
    def test_detailed_status_wins_over_stale_homepage(self):
        old = {"outputData": {"waterTemp": "38"}}
        new = {"events": [{"identifier": "post", "outputData": {"waterTemp": "39"}}]}
        self.assertEqual(p.extract_output_data({"statusInfo": old, "appDeviceStatusInfoEntity": {"statusInfo": new}})["waterTemp"], "39")

    def test_malformed_status_is_unknown(self):
        for raw in ('null', '[]', 'invalid', 3, {"events": [None]}, {"outputData": []}):
            self.assertEqual(p.extract_output_data({"statusInfo": raw}), {})

    def test_duration_boundaries_and_invalid_values(self):
        for n in (1, 5, 99):
            self.assertEqual(p.validate_integer(n, 1, 99), n)
        for n in (0, 100, 1.5, math.nan, math.inf):
            with self.assertRaises(ValueError):
                p.validate_integer(n, 1, 99)

    def test_temperature_range_and_flag(self):
        output = {"waterTemp": 38, "minTemp35": "1"}
        for value in (35, 50, 70):
            self.assertEqual(p.temperature_command(output, value), ("WaterTempSet", {"waterTemp": str(value)}))
        for value in (34, 71, 38.5, math.nan, math.inf):
            with self.assertRaises(ValueError):
                p.temperature_command(output, value)
        output['minTemp35'] = '0'
        with self.assertRaises(ValueError):
            p.temperature_command(output, 35)

    def test_half_degree_devices(self):
        output = {"waterTemp": 38, "halfTempSetFlag": 1}
        self.assertEqual(p.temperature_command(output, 38.5), ('SetHalfTempValue', {'waterTemp': '77'}))
        with self.assertRaises(ValueError):
            p.temperature_command(output, 50.5)

    def test_official_hot_water_in_use_interlock(self):
        for output, value in (({'waterTemp': 38, 'haveWater': 1}, 51), ({'waterTemp': 50, 'haveWaterUp': '1'}, 51)):
            with self.assertRaises(ValueError):
                p.temperature_command(output, value)
        self.assertEqual(p.temperature_command({'waterTemp': 38, 'haveWater': 1}, 50)[1], {'waterTemp': '50'})
        self.assertEqual(p.temperature_command({'waterTemp': 55, 'haveWater': 1}, 40)[1], {'waterTemp': '40'})

    def test_unknown_not_zero(self):
        self.assertIsNone(p.numeric({}, 'waterTemp'))
        self.assertIsNone(p.flag({}, 'heating'))
        self.assertIsNone(p.numeric({'waterTemp': 'nan'}, 'waterTemp'))
        self.assertFalse(p.flag({'heating': 0}, 'heating'))
        self.assertTrue(p.flag({'heating': '1'}, 'heating'))


if __name__ == '__main__':
    unittest.main()

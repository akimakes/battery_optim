import unittest

from run_simulation import build_battery_config


class RunSimulationTests(unittest.TestCase):
    def test_build_battery_config_converts_soc_fractions_to_kwh(self):
        config = {
            "battery": {
                "capacity_kwh": 10.0,
                "min_soc_fraction": 0.1,
                "max_soc_fraction": 0.9,
                "max_charge_kw": 2.0,
                "max_discharge_kw": 3.0,
                "battery_charge_efficiency": 0.95,
                "battery_discharge_efficiency": 0.94,
                "inverter_charge_efficiency": 0.97,
                "inverter_discharge_efficiency": 0.96,
            }
        }

        battery = build_battery_config(config)

        self.assertEqual(battery.initial_soc_kwh, 5.0)
        self.assertEqual(battery.min_soc_kwh, 1.0)
        self.assertEqual(battery.max_soc_kwh, 9.0)

    def test_build_battery_config_rejects_invalid_soc_fraction(self):
        config = {
            "battery": {
                "capacity_kwh": 10.0,
                "min_soc_fraction": 1.1,
                "max_soc_fraction": 0.9,
                "max_charge_kw": 2.0,
                "max_discharge_kw": 3.0,
                "battery_charge_efficiency": 0.95,
                "battery_discharge_efficiency": 0.94,
                "inverter_charge_efficiency": 0.97,
                "inverter_discharge_efficiency": 0.96,
            }
        }

        with self.assertRaises(ValueError):
            build_battery_config(config)


if __name__ == "__main__":
    unittest.main()

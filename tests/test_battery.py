import unittest

from batt.battery import Battery, BatteryConfig


def default_config() -> BatteryConfig:
    return BatteryConfig(
        capacity_kwh=10.0,
        initial_soc_kwh=5.0,
        min_soc_kwh=1.0,
        max_soc_kwh=9.0,
        max_charge_kw=4.0,
        max_discharge_kw=4.0,
        battery_charge_efficiency=0.95,
        battery_discharge_efficiency=0.95,
        inverter_charge_efficiency=0.97,
        inverter_discharge_efficiency=0.97,
    )


class BatteryTests(unittest.TestCase):
    def test_charge_reports_accepted_energy(self):
        battery = Battery(default_config())
        step = battery.step(charge_power_kw=2.0, discharge_power_kw=0.0, duration_hours=1.0)

        self.assertAlmostEqual(step.accepted_charge_kwh_ac, 2.0)
        self.assertAlmostEqual(step.soc_end_kwh, 5.0 + 2.0 * 0.95 * 0.97)

    def test_charge_is_capped_by_max_soc(self):
        battery = Battery(default_config())
        step = battery.step(charge_power_kw=4.0, discharge_power_kw=0.0, duration_hours=10.0)

        self.assertAlmostEqual(step.soc_end_kwh, 9.0)
        self.assertGreater(step.blocked_charge_kwh_ac, 0.0)

    def test_discharge_is_capped_by_min_soc(self):
        battery = Battery(default_config())
        step = battery.step(charge_power_kw=0.0, discharge_power_kw=4.0, duration_hours=10.0)

        self.assertAlmostEqual(step.soc_end_kwh, 1.0)
        self.assertGreater(step.blocked_discharge_kwh_ac, 0.0)


if __name__ == "__main__":
    unittest.main()

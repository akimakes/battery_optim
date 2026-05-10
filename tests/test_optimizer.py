import unittest

import pandas as pd

from batt.battery import BatteryConfig
from batt.optimizer import RuleParameterOptimizerConfig, _build_parameter_tasks, optimize_rule_parameters


class OptimizerTests(unittest.TestCase):
    def test_optimizer_skips_equal_and_inverted_thresholds(self):
        optimizer = RuleParameterOptimizerConfig(
            enabled=True,
            objective="maximize_savings_eur",
            cpu_cores=1,
            low_price_min_eur_per_kwh=0.10,
            low_price_max_eur_per_kwh=0.20,
            high_price_min_eur_per_kwh=0.10,
            high_price_max_eur_per_kwh=0.20,
            price_step_eur_per_kwh=0.10,
        )

        self.assertEqual(_build_parameter_tasks(optimizer), [(0.1, 0.2)])

    def test_optimizer_returns_best_rule_parameters(self):
        df = pd.DataFrame(
            {
                "datetime_start": pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC"),
                "datetime_end": pd.date_range("2024-01-01 00:15", periods=4, freq="15min", tz="UTC"),
                "consumption_kwh": [0.1, 0.1, 0.5, 0.5],
                "import_price_eur_per_kwh": [0.01, 0.01, 0.30, 0.30],
            }
        )
        battery = BatteryConfig(
            capacity_kwh=1.0,
            initial_soc_kwh=0.0,
            min_soc_kwh=0.0,
            max_soc_kwh=1.0,
            max_charge_kw=2.0,
            max_discharge_kw=2.0,
            battery_charge_efficiency=1.0,
            battery_discharge_efficiency=1.0,
            inverter_charge_efficiency=1.0,
            inverter_discharge_efficiency=1.0,
        )
        optimizer = RuleParameterOptimizerConfig(
            enabled=True,
            objective="maximize_savings_eur",
            cpu_cores=1,
            low_price_min_eur_per_kwh=0.00,
            low_price_max_eur_per_kwh=0.02,
            high_price_min_eur_per_kwh=0.20,
            high_price_max_eur_per_kwh=0.30,
            price_step_eur_per_kwh=0.10,
        )

        result = optimize_rule_parameters(
            df=df,
            battery_config=battery,
            baseline_energy_cost_eur=0.32,
            optimizer_config=optimizer,
        )

        self.assertGreater(result.summary.savings_eur, 0.0)
        self.assertEqual(result.controller_config.low_price_eur_per_kwh, 0.0)
        self.assertEqual(result.controller_config.high_price_eur_per_kwh, 0.2)
        self.assertFalse(result.trials.empty)


if __name__ == "__main__":
    unittest.main()

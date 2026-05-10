import unittest

from batt.simulation import RuleBasedControllerConfig


class SimulationTests(unittest.TestCase):
    def test_rule_based_controller_rejects_equal_thresholds(self):
        config = RuleBasedControllerConfig(
            low_price_eur_per_kwh=0.1,
            high_price_eur_per_kwh=0.1,
        )

        with self.assertRaises(ValueError):
            config.validate()


if __name__ == "__main__":
    unittest.main()

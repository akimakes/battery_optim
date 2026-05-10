import unittest

import pandas as pd

from batt.tariff import TariffConfig, billable_import_price


class TariffTests(unittest.TestCase):
    def test_awattar_markup_and_vat_are_applied(self):
        prices = pd.Series([0.10, -0.05])
        config = TariffConfig(
            awattar_markup_eur_per_kwh=0.015,
            vat_rate=0.20,
            monthly_base_fee_eur=5.75,
            grid_fees_eur_per_kwh=0.0,
            taxes_and_grid_cost_factor=0.0,
        )

        result = billable_import_price(prices, config)

        self.assertAlmostEqual(result.iloc[0], 0.138)
        self.assertAlmostEqual(result.iloc[1], -0.042)

    def test_taxes_and_grid_cost_factor_scales_energy_cost(self):
        prices = pd.Series([0.10])
        config = TariffConfig(
            awattar_markup_eur_per_kwh=0.015,
            vat_rate=0.20,
            monthly_base_fee_eur=5.75,
            grid_fees_eur_per_kwh=0.0,
            taxes_and_grid_cost_factor=1.0,
        )

        result = billable_import_price(prices, config)

        self.assertAlmostEqual(result.iloc[0], 0.276)


if __name__ == "__main__":
    unittest.main()

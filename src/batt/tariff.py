from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TariffConfig:
    awattar_markup_eur_per_kwh: float
    vat_rate: float
    monthly_base_fee_eur: float
    grid_fees_eur_per_kwh: float
    taxes_and_grid_cost_factor: float

    def validate(self) -> None:
        if self.vat_rate < 0:
            raise ValueError("VAT rate must be non-negative.")
        if self.monthly_base_fee_eur < 0:
            raise ValueError("Monthly base fee must be non-negative.")
        if self.taxes_and_grid_cost_factor < 0:
            raise ValueError("Taxes and grid cost factor must be non-negative.")


def billable_import_price(marketprice_eur_per_kwh: pd.Series, config: TariffConfig) -> pd.Series:
    config.validate()
    energy_price = marketprice_eur_per_kwh + config.awattar_markup_eur_per_kwh
    estimated_taxes_and_grid_costs = energy_price * config.taxes_and_grid_cost_factor
    variable_price = energy_price + estimated_taxes_and_grid_costs + config.grid_fees_eur_per_kwh
    return variable_price * (1.0 + config.vat_rate)


def baseline_energy_cost(df: pd.DataFrame, price_column: str = "import_price_eur_per_kwh") -> float:
    return float((df["consumption_kwh"] * df[price_column]).sum())

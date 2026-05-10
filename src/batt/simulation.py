from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from batt.battery import Battery, BatteryConfig


@dataclass(frozen=True)
class RuleBasedControllerConfig:
    low_price_eur_per_kwh: float
    high_price_eur_per_kwh: float

    def validate(self) -> None:
        if self.low_price_eur_per_kwh >= self.high_price_eur_per_kwh:
            raise ValueError("Low price threshold must be lower than high price threshold.")


def simulate_rule_based(
    df: pd.DataFrame,
    battery_config: BatteryConfig,
    controller_config: RuleBasedControllerConfig,
    price_column: str = "import_price_eur_per_kwh",
) -> pd.DataFrame:
    controller_config.validate()
    battery = Battery(battery_config)
    rows = []

    for row in df.itertuples(index=False):
        duration_hours = (row.datetime_end - row.datetime_start).total_seconds() / 3600.0
        price = getattr(row, price_column)
        consumption_kwh = row.consumption_kwh

        charge_kw = battery_config.max_charge_kw if price <= controller_config.low_price_eur_per_kwh else 0.0
        discharge_kw = 0.0
        if price >= controller_config.high_price_eur_per_kwh:
            discharge_kw = min(battery_config.max_discharge_kw, consumption_kwh / duration_hours)

        step = battery.step(
            charge_power_kw=charge_kw,
            discharge_power_kw=discharge_kw,
            duration_hours=duration_hours,
        )

        battery_to_house = min(step.delivered_discharge_kwh_ac, consumption_kwh)
        grid_to_house = consumption_kwh - battery_to_house
        grid_import = grid_to_house + step.accepted_charge_kwh_ac

        rows.append(
            {
                "datetime_start": row.datetime_start,
                "datetime_end": row.datetime_end,
                "consumption_kwh": consumption_kwh,
                price_column: price,
                "soc_start_kwh": step.soc_start_kwh,
                "soc_end_kwh": step.soc_end_kwh,
                "grid_import_kwh": grid_import,
                "grid_to_house_kwh": grid_to_house,
                "battery_charge_kwh_ac": step.accepted_charge_kwh_ac,
                "battery_discharge_kwh_ac": battery_to_house,
                "blocked_charge_kwh_ac": step.blocked_charge_kwh_ac,
                "blocked_discharge_kwh_ac": step.blocked_discharge_kwh_ac,
                "cost_eur": grid_import * price,
            }
        )

    return pd.DataFrame(rows)

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SimulationSummary:
    intervals: int
    consumption_kwh: float
    baseline_energy_cost_eur: float
    battery_energy_cost_eur: float
    savings_eur: float
    grid_import_kwh: float
    battery_charge_kwh_ac: float
    battery_discharge_kwh_ac: float
    battery_losses_kwh: float
    equivalent_full_cycles: float


def summarize(
    df: pd.DataFrame,
    capacity_kwh: float,
    baseline_energy_cost_eur: float,
) -> SimulationSummary:
    battery_energy_cost = float(df["cost_eur"].sum())
    charge = float(df["battery_charge_kwh_ac"].sum())
    discharge = float(df["battery_discharge_kwh_ac"].sum())
    losses = charge - discharge
    return SimulationSummary(
        intervals=len(df),
        consumption_kwh=float(df["consumption_kwh"].sum()),
        baseline_energy_cost_eur=baseline_energy_cost_eur,
        battery_energy_cost_eur=battery_energy_cost,
        savings_eur=baseline_energy_cost_eur - battery_energy_cost,
        grid_import_kwh=float(df["grid_import_kwh"].sum()),
        battery_charge_kwh_ac=charge,
        battery_discharge_kwh_ac=discharge,
        battery_losses_kwh=losses,
        equivalent_full_cycles=discharge / capacity_kwh if capacity_kwh > 0 else 0.0,
    )

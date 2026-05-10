#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from batt.battery import BatteryConfig
from batt.config import load_config
from batt.data_preparation import prepare_input_data
from batt.data_io import filter_latest_days, read_interval_data
from batt.optimizer import RuleParameterOptimizerConfig, optimize_rule_parameters
from batt.plotting import PlotConfig, plot_month
from batt.results import summarize
from batt.simulation import RuleBasedControllerConfig, simulate_rule_based
from batt.tariff import TariffConfig, baseline_energy_cost, billable_import_price


def build_battery_config(config: dict) -> BatteryConfig:
    battery_config = dict(config["battery"])
    capacity_kwh = battery_config["capacity_kwh"]
    initial_soc_fraction = 0.5
    for key in ("min_soc_fraction", "max_soc_fraction"):
        value = battery_config[key]
        if not 0 <= value <= 1:
            raise ValueError(f"battery.{key} must be in the interval [0, 1].")
    return BatteryConfig(
        capacity_kwh=capacity_kwh,
        initial_soc_kwh=capacity_kwh * initial_soc_fraction,
        min_soc_kwh=capacity_kwh * battery_config["min_soc_fraction"],
        max_soc_kwh=capacity_kwh * battery_config["max_soc_fraction"],
        max_charge_kw=battery_config["max_charge_kw"],
        max_discharge_kw=battery_config["max_discharge_kw"],
        battery_charge_efficiency=battery_config["battery_charge_efficiency"],
        battery_discharge_efficiency=battery_config["battery_discharge_efficiency"],
        inverter_charge_efficiency=battery_config["inverter_charge_efficiency"],
        inverter_discharge_efficiency=battery_config["inverter_discharge_efficiency"],
    )


def build_tariff_config(config: dict) -> TariffConfig:
    return TariffConfig(**config["tariff"])


def build_rule_based_controller_config(config: dict) -> RuleBasedControllerConfig:
    return RuleBasedControllerConfig(**config["rule_based_controller"])


def build_optimizer_config(config: dict) -> RuleParameterOptimizerConfig:
    return RuleParameterOptimizerConfig(**config["optimizer"])


def build_plot_config(config: dict) -> PlotConfig:
    return PlotConfig(**config["plot"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a battery bill simulation.")
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="YAML config file. Default: config/default.yaml",
    )
    args = parser.parse_args()

    config = load_config(PROJECT_ROOT / args.config)
    prepared_input_csv = prepare_input_data(config, PROJECT_ROOT)
    df = read_interval_data(prepared_input_csv)
    df = filter_latest_days(df, config["simulation"]["time_range_days"])
    tariff = build_tariff_config(config)
    battery = build_battery_config(config)
    controller = build_rule_based_controller_config(config)
    optimizer = build_optimizer_config(config)
    plot = build_plot_config(config)

    df["import_price_eur_per_kwh"] = billable_import_price(
        df["marketprice_eur_per_kwh"],
        tariff,
    )

    baseline_cost = baseline_energy_cost(df)

    if optimizer.enabled:
        result = optimize_rule_parameters(
            df=df,
            battery_config=battery,
            baseline_energy_cost_eur=baseline_cost,
            optimizer_config=optimizer,
        )
        optimization_output_path = PROJECT_ROOT / config["data"]["optimization_output_csv"]
        optimization_output_path.parent.mkdir(parents=True, exist_ok=True)
        result.trials.to_csv(optimization_output_path, index=False)

        controller = result.controller_config
        print("Best rule-based controller parameters")
        print(f"low_price_eur_per_kwh: {controller.low_price_eur_per_kwh:.3f}")
        print(f"high_price_eur_per_kwh: {controller.high_price_eur_per_kwh:.3f}")
        print(f"optimization_output_csv: {optimization_output_path}")

    simulated = simulate_rule_based(
        df=df,
        battery_config=battery,
        controller_config=controller,
    )
    summary = summarize(
        simulated,
        capacity_kwh=battery.capacity_kwh,
        baseline_energy_cost_eur=baseline_cost,
    )

    output_path = PROJECT_ROOT / config["data"]["simulation_output_csv"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    simulated.to_csv(output_path, index=False)
    print(f"output_csv: {output_path}")

    if plot.enabled:
        plot_output_path = PROJECT_ROOT / plot.output_file
        plot_month(simulated, plot, plot_output_path)
        print(f"plot_output_file: {plot_output_path}")

    print("Simulation summary")
    for key, value in asdict(summary).items():
        if isinstance(value, float):
            print(f"{key}: {value:.3f}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import pandas as pd

from batt.battery import BatteryConfig
from batt.results import SimulationSummary, summarize
from batt.simulation import RuleBasedControllerConfig, simulate_rule_based


_WORKER_DF: pd.DataFrame | None = None
_WORKER_BATTERY_CONFIG: BatteryConfig | None = None
_WORKER_BASELINE_COST: float | None = None


@dataclass(frozen=True)
class RuleParameterOptimizerConfig:
    enabled: bool
    objective: str
    cpu_cores: int
    low_price_min_eur_per_kwh: float
    low_price_max_eur_per_kwh: float
    high_price_min_eur_per_kwh: float
    high_price_max_eur_per_kwh: float
    price_step_eur_per_kwh: float

    def validate(self) -> None:
        if self.objective != "maximize_savings_eur":
            raise ValueError("Only objective 'maximize_savings_eur' is supported.")
        if self.cpu_cores < 1:
            raise ValueError("Optimizer CPU cores must be >= 1.")
        if self.price_step_eur_per_kwh <= 0:
            raise ValueError("Optimizer price step must be positive.")
        if self.low_price_min_eur_per_kwh > self.low_price_max_eur_per_kwh:
            raise ValueError("Low-price optimizer range is invalid.")
        if self.high_price_min_eur_per_kwh > self.high_price_max_eur_per_kwh:
            raise ValueError("High-price optimizer range is invalid.")


@dataclass(frozen=True)
class RuleParameterOptimizationResult:
    controller_config: RuleBasedControllerConfig
    summary: SimulationSummary
    trials: pd.DataFrame


def optimize_rule_parameters(
    df: pd.DataFrame,
    battery_config: BatteryConfig,
    baseline_energy_cost_eur: float,
    optimizer_config: RuleParameterOptimizerConfig,
) -> RuleParameterOptimizationResult:
    optimizer_config.validate()
    tasks = _build_parameter_tasks(optimizer_config)
    if not tasks:
        raise ValueError("Optimizer produced no valid controller parameter pairs.")

    if optimizer_config.cpu_cores == 1:
        evaluated_trials = [
            _evaluate_rule_parameter_task(
                task,
                df=df,
                battery_config=battery_config,
                baseline_energy_cost_eur=baseline_energy_cost_eur,
            )
            for task in tasks
        ]
    else:
        max_workers = min(optimizer_config.cpu_cores, os.cpu_count() or 1, len(tasks))
        with ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=_init_worker,
            initargs=(df, battery_config, baseline_energy_cost_eur),
        ) as executor:
            evaluated_trials = list(executor.map(_evaluate_rule_parameter_task_in_worker, tasks))

    trial_rows = []
    best_controller = None
    best_summary = None
    best_savings = None

    for controller, summary in evaluated_trials:
        trial_rows.append(
            {
                "low_price_eur_per_kwh": controller.low_price_eur_per_kwh,
                "high_price_eur_per_kwh": controller.high_price_eur_per_kwh,
                "savings_eur": summary.savings_eur,
                "battery_energy_cost_eur": summary.battery_energy_cost_eur,
                "battery_charge_kwh_ac": summary.battery_charge_kwh_ac,
                "battery_discharge_kwh_ac": summary.battery_discharge_kwh_ac,
                "equivalent_full_cycles": summary.equivalent_full_cycles,
            }
        )

        if best_savings is None or summary.savings_eur > best_savings:
            best_savings = summary.savings_eur
            best_controller = controller
            best_summary = summary

    if best_controller is None or best_summary is None:
        raise ValueError("Optimizer produced no valid controller parameter pairs.")

    return RuleParameterOptimizationResult(
        controller_config=best_controller,
        summary=best_summary,
        trials=pd.DataFrame(trial_rows),
    )


def _build_parameter_tasks(optimizer_config: RuleParameterOptimizerConfig) -> list[tuple[float, float]]:
    tasks = []
    for low_price in _inclusive_range(
        optimizer_config.low_price_min_eur_per_kwh,
        optimizer_config.low_price_max_eur_per_kwh,
        optimizer_config.price_step_eur_per_kwh,
    ):
        for high_price in _inclusive_range(
            optimizer_config.high_price_min_eur_per_kwh,
            optimizer_config.high_price_max_eur_per_kwh,
            optimizer_config.price_step_eur_per_kwh,
        ):
            if low_price < high_price:
                tasks.append((low_price, high_price))
    return tasks


def _evaluate_rule_parameter_task(
    task: tuple[float, float],
    df: pd.DataFrame,
    battery_config: BatteryConfig,
    baseline_energy_cost_eur: float,
) -> tuple[RuleBasedControllerConfig, SimulationSummary]:
    low_price, high_price = task
    controller = RuleBasedControllerConfig(
        low_price_eur_per_kwh=low_price,
        high_price_eur_per_kwh=high_price,
    )
    simulated = simulate_rule_based(
        df=df,
        battery_config=battery_config,
        controller_config=controller,
    )
    summary = summarize(
        simulated,
        capacity_kwh=battery_config.capacity_kwh,
        baseline_energy_cost_eur=baseline_energy_cost_eur,
    )
    return controller, summary


def _init_worker(
    df: pd.DataFrame,
    battery_config: BatteryConfig,
    baseline_energy_cost_eur: float,
) -> None:
    global _WORKER_DF, _WORKER_BATTERY_CONFIG, _WORKER_BASELINE_COST
    _WORKER_DF = df
    _WORKER_BATTERY_CONFIG = battery_config
    _WORKER_BASELINE_COST = baseline_energy_cost_eur


def _evaluate_rule_parameter_task_in_worker(
    task: tuple[float, float],
) -> tuple[RuleBasedControllerConfig, SimulationSummary]:
    if _WORKER_DF is None or _WORKER_BATTERY_CONFIG is None or _WORKER_BASELINE_COST is None:
        raise RuntimeError("Optimizer worker was not initialized.")
    return _evaluate_rule_parameter_task(
        task,
        df=_WORKER_DF,
        battery_config=_WORKER_BATTERY_CONFIG,
        baseline_energy_cost_eur=_WORKER_BASELINE_COST,
    )


def _inclusive_range(start: float, stop: float, step: float) -> list[float]:
    values = []
    current = start
    epsilon = step / 10.0
    while current <= stop + epsilon:
        values.append(round(current, 10))
        current += step
    return values

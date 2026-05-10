from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


@dataclass(frozen=True)
class PlotConfig:
    enabled: bool
    year: int
    month: int
    timezone: str
    output_file: str

    def validate(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError("Plot month must be in the interval 1..12.")


def filter_plot_month(df: pd.DataFrame, config: PlotConfig) -> pd.DataFrame:
    config.validate()
    local_start = df["datetime_start"].dt.tz_convert(config.timezone)
    mask = (local_start.dt.year == config.year) & (local_start.dt.month == config.month)
    filtered = df.loc[mask].copy()
    if filtered.empty:
        raise ValueError(f"No simulation rows found for {config.year:04d}-{config.month:02d}.")
    filtered["plot_datetime"] = filtered["datetime_start"].dt.tz_convert(config.timezone)
    return filtered


def plot_month(df: pd.DataFrame, config: PlotConfig, output_path: str | Path) -> None:
    month_df = filter_plot_month(df, config)
    x = month_df["plot_datetime"]

    fig, axes = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(16, 10),
        sharex=True,
        constrained_layout=True,
    )

    axes[0].plot(x, month_df["import_price_eur_per_kwh"], color="black", linewidth=1.0)
    axes[0].set_ylabel("Price [EUR/kWh]")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(x, month_df["consumption_kwh"], label="House consumption", color="#1f77b4", linewidth=0.9)
    axes[1].plot(x, month_df["grid_import_kwh"], label="Grid import", color="#d62728", linewidth=0.9)
    axes[1].plot(x, month_df["battery_charge_kwh_ac"], label="Battery charge", color="#2ca02c", linewidth=0.9)
    axes[1].plot(x, month_df["battery_discharge_kwh_ac"], label="Battery discharge", color="#ff7f0e", linewidth=0.9)
    axes[1].set_ylabel("Energy / 15 min [kWh]")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="upper right", ncols=2)

    axes[2].plot(x, month_df["soc_end_kwh"], color="#9467bd", linewidth=1.0)
    axes[2].set_ylabel("SOC [kWh]")
    axes[2].set_xlabel(f"Time [{config.timezone}]")
    axes[2].grid(True, alpha=0.25)

    axes[0].set_title(f"Battery simulation for {config.year:04d}-{config.month:02d}")
    axes[2].xaxis.set_major_locator(mdates.DayLocator(interval=2))
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m", tz=x.dt.tz))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)

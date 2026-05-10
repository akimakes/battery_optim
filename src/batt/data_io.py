from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd


REQUIRED_COLUMNS = {
    "datetime_start",
    "datetime_end",
    "consumption_kwh",
    "marketprice_eur_per_kwh",
}


def read_interval_data(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Input CSV missing column(s): {', '.join(sorted(missing))}")

    df["datetime_start"] = pd.to_datetime(df["datetime_start"], utc=True)
    df["datetime_end"] = pd.to_datetime(df["datetime_end"], utc=True)
    df["consumption_kwh"] = pd.to_numeric(df["consumption_kwh"])
    df["marketprice_eur_per_kwh"] = pd.to_numeric(df["marketprice_eur_per_kwh"])

    df = df.sort_values("datetime_start").reset_index(drop=True)
    validate_interval_data(df)
    return df


def validate_interval_data(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Input data is empty.")
    if df["datetime_start"].duplicated().any():
        raise ValueError("Input data contains duplicate interval starts.")
    if df[["datetime_start", "datetime_end", "consumption_kwh", "marketprice_eur_per_kwh"]].isna().any().any():
        raise ValueError("Input data contains missing values.")
    if (df["datetime_end"] <= df["datetime_start"]).any():
        raise ValueError("Every interval end must be after its start.")
    if (df["consumption_kwh"] < 0).any():
        raise ValueError("Consumption must be non-negative.")

    durations = df["datetime_end"] - df["datetime_start"]
    if durations.nunique() != 1:
        raise ValueError("All intervals must have the same duration.")

    gaps = df["datetime_start"].iloc[1:].reset_index(drop=True) - df["datetime_end"].iloc[:-1].reset_index(drop=True)
    if not gaps.empty and (gaps != pd.Timedelta(0)).any():
        raise ValueError("Input data contains gaps or overlapping intervals.")


def interval_hours(df: pd.DataFrame) -> float:
    duration = df["datetime_end"].iloc[0] - df["datetime_start"].iloc[0]
    return duration.total_seconds() / 3600.0


def filter_latest_days(df: pd.DataFrame, time_range_days: int | Literal["full"]) -> pd.DataFrame:
    if time_range_days == "full":
        return df.copy()

    try:
        days = int(time_range_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("simulation.time_range_days must be 'full' or a positive integer.") from exc

    if days <= 0:
        raise ValueError("simulation.time_range_days must be 'full' or a positive integer.")

    latest_end = df["datetime_end"].max()
    earliest_start = latest_end - pd.Timedelta(days=days)
    filtered = df[df["datetime_start"] >= earliest_start].copy()
    validate_interval_data(filtered)
    return filtered.reset_index(drop=True)

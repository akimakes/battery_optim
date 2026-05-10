from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from batt.data_io import validate_interval_data


PREPARED_INPUT_CSV = Path("data/input/data.csv")
INTERNAL_MERGED_CONSUMPTION_CSV = Path("data/input/house_consumption_merged.csv")
INTERNAL_PRICE_JSON = Path("data/price/awattar_fetched.json")
INTERNAL_PRICE_CSV = Path("data/price/awattar_fetched.csv")


@dataclass(frozen=True)
class DataPreparationConfig:
    enabled: bool
    consumption_timezone: str
    awattar_api_url: str


def build_data_preparation_config(config: dict) -> DataPreparationConfig:
    return DataPreparationConfig(**config["data_preparation"])


def prepare_input_data(config: dict, project_root: Path) -> Path:
    preparation = build_data_preparation_config(config)
    output_path = project_root / PREPARED_INPUT_CSV
    if not preparation.enabled:
        return output_path

    consumption_dir = project_root / config["data"]["house_consumption_dir"]
    consumption = read_consumption_directory(
        consumption_dir,
        timezone_name=preparation.consumption_timezone,
    )
    _write_internal_csv(consumption, project_root / INTERNAL_MERGED_CONSUMPTION_CSV)

    price_start = consumption["datetime"].min().floor("h")
    price_end = consumption["datetime"].max().ceil("h") + pd.Timedelta(hours=1)
    price_hourly = fetch_awattar_prices(
        api_url=preparation.awattar_api_url,
        start=price_start,
        end=price_end,
    )
    _write_price_artifacts(price_hourly, project_root)

    synchronized = synchronize_consumption_and_price(consumption, price_hourly)
    _write_internal_csv(synchronized, output_path)

    print("Data preparation summary")
    print(f"consumption_files: {len(_raw_consumption_csv_paths(consumption_dir))}")
    print(f"consumption_start: {synchronized['datetime_start'].min()}")
    print(f"consumption_end: {synchronized['datetime_end'].max()}")
    print(f"synchronized_rows: {len(synchronized)}")

    return output_path


def read_consumption_directory(path: Path, timezone_name: str) -> pd.DataFrame:
    csv_paths = _raw_consumption_csv_paths(path)
    if not csv_paths:
        raise ValueError(f"No raw consumption CSV files found in {path}.")

    frames = [
        _localize_consumption_frame(
            _read_raw_consumption_csv(csv_path),
            timezone_name=timezone_name,
        )
        for csv_path in csv_paths
    ]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[["datetime", "consumption_kwh"]].sort_values("datetime").reset_index(drop=True)

    if combined["datetime"].duplicated().any():
        combined = combined.drop_duplicates(subset=["datetime"], keep="last").reset_index(drop=True)

    return combined


def _localize_consumption_frame(df: pd.DataFrame, timezone_name: str) -> pd.DataFrame:
    df = df.copy()
    df["datetime"] = (
        df["datetime_local"]
        .dt.tz_localize(timezone_name, ambiguous="infer", nonexistent="shift_forward")
        .dt.tz_convert("UTC")
    )
    return df


def fetch_awattar_prices(api_url: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    response = _fetch_awattar_json(api_url, start, end)
    rows = response.get("data", [])
    if not rows:
        raise ValueError("aWATTar API returned no price data.")

    price = _awattar_json_rows_to_price_frame(rows)
    price = price.drop_duplicates(subset=["price_start"]).sort_values("price_start").reset_index(drop=True)
    if price.empty:
        raise ValueError("aWATTar API returned no usable price data.")
    price.attrs["raw_data"] = rows
    return price


def synchronize_consumption_and_price(consumption: pd.DataFrame, price_hourly: pd.DataFrame) -> pd.DataFrame:
    price_15min = expand_hourly_price_to_15min(price_hourly)
    joined = pd.merge(
        consumption,
        price_15min,
        on="datetime",
        how="inner",
    )
    joined = joined.sort_values("datetime").reset_index(drop=True)
    joined["datetime_end"] = joined["datetime"] + pd.Timedelta(minutes=15)
    joined = joined.rename(columns={"datetime": "datetime_start"})
    joined = joined[
        [
            "datetime_start",
            "datetime_end",
            "consumption_kwh",
            "marketprice_eur_per_kwh",
        ]
    ]
    validate_interval_data(joined)
    return joined


def expand_hourly_price_to_15min(price_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in price_df.itertuples(index=False):
        intervals = pd.date_range(
            start=row.price_start,
            end=row.price_end,
            freq="15min",
            inclusive="left",
        )
        for timestamp in intervals:
            rows.append(
                {
                    "datetime": timestamp,
                    "marketprice_eur_per_kwh": row.marketprice_eur_per_kwh,
                }
            )
    return pd.DataFrame(rows)


def _raw_consumption_csv_paths(path: Path) -> list[Path]:
    if not path.exists():
        raise ValueError(f"Consumption directory does not exist: {path}")
    return sorted(
        csv_path
        for csv_path in path.glob("*.csv")
        if "merged" not in csv_path.name.lower()
    )


def _read_raw_consumption_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    df = df.dropna(axis=1, how="all")

    required = {"Messzeitpunkt", "Verbrauch (kWh)"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing column(s): {', '.join(sorted(missing))}")

    df["datetime_local"] = pd.to_datetime(
        df["Messzeitpunkt"],
        format="%d.%m.%Y %H:%M",
    )
    df = df.rename(columns={"Verbrauch (kWh)": "consumption_kwh"})
    df["consumption_kwh"] = pd.to_numeric(df["consumption_kwh"])
    if (df["consumption_kwh"] < 0).any():
        raise ValueError(f"{path} contains negative consumption values.")
    return df[["datetime_local", "consumption_kwh"]]


def _fetch_awattar_json(api_url: str, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    query = urlencode(
        {
            "start": _timestamp_to_epoch_ms(start),
            "end": _timestamp_to_epoch_ms(end),
        }
    )
    with urlopen(f"{api_url}?{query}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _awattar_json_rows_to_price_frame(rows: list[dict]) -> pd.DataFrame:
    converted = []
    for row in rows:
        converted.append(
            {
                "price_start": pd.to_datetime(row["start_timestamp"], unit="ms", utc=True),
                "price_end": pd.to_datetime(row["end_timestamp"], unit="ms", utc=True),
                "marketprice_eur_per_kwh": float(row["marketprice"]) / 1000.0,
                "start_timestamp": row["start_timestamp"],
                "end_timestamp": row["end_timestamp"],
                "marketprice": row["marketprice"],
                "unit": row["unit"],
            }
        )
    return pd.DataFrame(converted)


def _write_price_artifacts(price_hourly: pd.DataFrame, project_root: Path) -> None:
    raw_json_path = project_root / INTERNAL_PRICE_JSON
    raw_json_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_json_path.open("w", encoding="utf-8") as f:
        json.dump({"object": "list", "data": price_hourly.attrs.get("raw_data", [])}, f, indent=2)

    csv = price_hourly[
        [
            "price_start",
            "price_end",
            "start_timestamp",
            "end_timestamp",
            "marketprice",
            "unit",
        ]
    ].rename(columns={"price_start": "start_datetime", "price_end": "end_datetime"})
    _write_internal_csv(csv, project_root / INTERNAL_PRICE_CSV)


def _write_internal_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _timestamp_to_epoch_ms(timestamp: pd.Timestamp) -> int:
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    timestamp = timestamp.tz_convert(timezone.utc)
    return int(timestamp.timestamp() * 1000)

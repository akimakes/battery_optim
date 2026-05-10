#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from batt.config import load_config


def read_price_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = {"start_datetime", "end_datetime", "marketprice"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Price CSV missing column(s): {', '.join(missing)}")

    df["price_start"] = pd.to_datetime(df["start_datetime"], utc=True)
    df["price_end"] = pd.to_datetime(df["end_datetime"], utc=True)

    # Convert Eur/MWh to Eur/kWh
    df["marketprice_eur_per_kwh"] = df["marketprice"] / 1000.0

    return df[["price_start", "price_end", "marketprice_eur_per_kwh"]].copy()


def expand_hourly_price_to_15min(price_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in price_df.iterrows():
        intervals = pd.date_range(
            start=row["price_start"],
            end=row["price_end"],
            freq="15min",
            inclusive="left",
        )

        for t in intervals:
            rows.append(
                {
                    "datetime": t,
                    "marketprice_eur_per_kwh": row["marketprice_eur_per_kwh"],
                }
            )

    return pd.DataFrame(rows)


def read_consumption_csv(path: str, timezone: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep=";",
        decimal=",",
        encoding="utf-8-sig",
    )

    df = df.dropna(axis=1, how="all")

    required = {"Messzeitpunkt", "Verbrauch (kWh)"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Consumption CSV missing column(s): {', '.join(missing)}")

    df["datetime_local"] = pd.to_datetime(
        df["Messzeitpunkt"],
        format="%d.%m.%Y %H:%M",
    )

    df["datetime"] = (
        df["datetime_local"]
        .dt.tz_localize(timezone, ambiguous="infer", nonexistent="shift_forward")
        .dt.tz_convert("UTC")
    )

    df = df.rename(columns={"Verbrauch (kWh)": "consumption_kwh"})

    return df[["datetime", "consumption_kwh"]].copy()


def synchronize(price_csv: str, consumption_csv: str, output_csv: str, timezone: str) -> None:
    price_hourly = read_price_csv(price_csv)
    price_15min = expand_hourly_price_to_15min(price_hourly)
    consumption = read_consumption_csv(consumption_csv, timezone)

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

    output_path = Path(output_csv)
    joined.to_csv(output_path, index=False)

    print(f"Written synchronized CSV to: {output_path}")
    print(f"Rows written: {len(joined)}")

    if len(joined) > 0:
        print(f"Start: {joined['datetime_start'].min()}")
        print(f"End:   {joined['datetime_end'].max()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize hourly aWATTar marketprice data with 15-minute "
            "house consumption data. Output is in 15-minute intervals with "
            "marketprice converted to EUR/kWh."
        )
    )

    parser.add_argument(
        "-price",
        required=True,
        help="Input aWATTar marketprice CSV with hourly data",
    )

    parser.add_argument(
        "-cons",
        required=True,
        help="Input house consumption CSV with 15-minute data",
    )

    parser.add_argument(
        "-out",
        required=True,
        help="Output synchronized CSV",
    )

    parser.add_argument(
        "-tz",
        default=None,
        help="Override YAML: timezone of the consumption timestamps.",
    )

    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="YAML config file. Default: config/default.yaml",
    )

    args = parser.parse_args()
    config = load_config(PROJECT_ROOT / args.config)
    timezone = args.tz if args.tz is not None else config["data_preparation"]["consumption_timezone"]

    synchronize(
        price_csv=args.price,
        consumption_csv=args.cons,
        output_csv=args.out,
        timezone=timezone,
    )


if __name__ == "__main__":
    main()

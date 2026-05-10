#!/usr/bin/env python3

import argparse
import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


REFERENCE_YEAR = 2000  # Leap year, so Feb 29 can be plotted if present


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.strip())


def midpoint_datetime(start: datetime, end: datetime) -> datetime:
    return start + (end - start) / 2


def normalize_to_reference_year(dt: datetime) -> datetime:
    return dt.replace(year=REFERENCE_YEAR)


def duration_hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def read_marketprice_csv(csv_path: str):
    data_by_year = {}

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if "marketprice" in reader.fieldnames:
            price_column = "marketprice"
        elif "markedprice" in reader.fieldnames:
            price_column = "markedprice"
        else:
            raise ValueError(
                "CSV must contain either a 'marketprice' or 'markedprice' column."
            )

        required_columns = {"start_datetime", "end_datetime", price_column}
        missing = required_columns - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required column(s): {', '.join(missing)}")

        for row in reader:
            start_dt = parse_datetime(row["start_datetime"])
            end_dt = parse_datetime(row["end_datetime"])

            midpoint = midpoint_datetime(start_dt, end_dt)
            original_year = midpoint.year
            normalized_midpoint = normalize_to_reference_year(midpoint)

            marketprice = float(row[price_column])
            hours = duration_hours(start_dt, end_dt)

            if original_year not in data_by_year:
                data_by_year[original_year] = {
                    "x": [],
                    "y": [],
                    "negative_hours": 0.0,
                }

            data_by_year[original_year]["x"].append(normalized_midpoint)
            data_by_year[original_year]["y"].append(marketprice)

            if marketprice < 0:
                data_by_year[original_year]["negative_hours"] += hours

    return data_by_year


def format_hours(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}"


def plot_marketprice(data_by_year, output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(14, 7))

    for year in sorted(data_by_year):
        x = data_by_year[year]["x"]
        y = data_by_year[year]["y"]
        negative_hours = data_by_year[year]["negative_hours"]

        paired = sorted(zip(x, y), key=lambda item: item[0])
        x_sorted = [item[0] for item in paired]
        y_sorted = [item[1] for item in paired]

        label = f"{year} ({format_hours(negative_hours)} h < 0 EUR)"

        ax.plot(
            x_sorted,
            y_sorted,
            linewidth=1.2,
            label=label,
        )

    ax.set_title("Market price by day of year")
    ax.set_xlabel("Month")
    ax.set_ylabel("Market price [Eur/MWh]")

    ax.set_xlim(
        datetime(REFERENCE_YEAR, 1, 1),
        datetime(REFERENCE_YEAR + 1, 1, 1),
    )

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    ax.grid(True, alpha=0.3)
    ax.legend(title="Year and negative-price hours", loc="best")

    fig.tight_layout()

    output_path = Path(output_path)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    print(f"Plot written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Plot marketprice over the midpoint between start_datetime and "
            "end_datetime. Multiple years are overlaid on a single Jan-Dec axis. "
            "The legend includes the number of hours with negative marketprice."
        )
    )

    parser.add_argument(
        "-in",
        dest="input_csv",
        required=True,
        help="Input CSV file",
    )

    parser.add_argument(
        "-out",
        dest="output_plot",
        required=True,
        help="Output plot file, e.g. marketprice.svg, marketprice.png, marketprice.pdf",
    )

    args = parser.parse_args()

    data_by_year = read_marketprice_csv(args.input_csv)
    plot_marketprice(data_by_year, args.output_plot)


if __name__ == "__main__":
    main()
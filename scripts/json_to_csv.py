import json
import csv
import argparse
from datetime import datetime, timezone
from pathlib import Path


def epoch_ms_to_datetime_string(epoch_ms: int) -> str:
    """
    Convert Unix epoch timestamp in milliseconds to an ISO 8601
    datetime string in UTC.
    """
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()


def json_to_csv(input_json: str, output_csv: str) -> None:
    input_path = Path(input_json)
    output_path = Path(output_csv)

    with input_path.open("r", encoding="utf-8") as f:
        json_data = json.load(f)

    rows = json_data["data"]

    converted_rows = []
    for row in rows:
        converted_rows.append({
            "start_datetime": epoch_ms_to_datetime_string(row["start_timestamp"]),
            "end_datetime": epoch_ms_to_datetime_string(row["end_timestamp"]),
            "start_timestamp": row["start_timestamp"],
            "end_timestamp": row["end_timestamp"],
            "marketprice": row["marketprice"],
            "unit": row["unit"],
        })

    fieldnames = [
        "start_datetime",
        "end_datetime",
        "start_timestamp",
        "end_timestamp",
        "marketprice",
        "unit",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(converted_rows)

    print(f"CSV written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert awattar-style JSON market data to CSV."
    )

    parser.add_argument(
        "-in",
        dest="input_json",
        required=True,
        help="Input JSON file path",
    )

    parser.add_argument(
        "-out",
        dest="output_csv",
        required=True,
        help="Output CSV file path",
    )

    args = parser.parse_args()

    json_to_csv(args.input_json, args.output_csv)


if __name__ == "__main__":
    main()
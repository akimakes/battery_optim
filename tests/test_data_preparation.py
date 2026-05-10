import unittest
from pathlib import Path

import pandas as pd

from batt.data_preparation import (
    _raw_consumption_csv_paths,
    expand_hourly_price_to_15min,
    synchronize_consumption_and_price,
)


class DataPreparationTests(unittest.TestCase):
    def test_raw_consumption_csv_paths_ignore_merged_files(self):
        directory = Path(".test-tmp") / "consumption"
        directory.mkdir(parents=True, exist_ok=True)
        raw = directory / "segment.csv"
        merged = directory / "segment-merged.csv"
        raw.write_text("", encoding="utf-8")
        merged.write_text("", encoding="utf-8")

        try:
            self.assertEqual(_raw_consumption_csv_paths(directory), [raw])
        finally:
            raw.unlink(missing_ok=True)
            merged.unlink(missing_ok=True)
            directory.rmdir()

    def test_expand_hourly_price_to_15min_repeats_hour_price(self):
        price = pd.DataFrame(
            {
                "price_start": pd.to_datetime(["2025-01-01 00:00:00+00:00"], utc=True),
                "price_end": pd.to_datetime(["2025-01-01 01:00:00+00:00"], utc=True),
                "marketprice_eur_per_kwh": [0.1],
            }
        )

        expanded = expand_hourly_price_to_15min(price)

        self.assertEqual(len(expanded), 4)
        self.assertTrue((expanded["marketprice_eur_per_kwh"] == 0.1).all())

    def test_synchronize_consumption_and_price_outputs_interval_schema(self):
        start = pd.date_range("2025-01-01", periods=4, freq="15min", tz="UTC")
        consumption = pd.DataFrame(
            {
                "datetime": start,
                "consumption_kwh": [0.1, 0.2, 0.3, 0.4],
            }
        )
        price = pd.DataFrame(
            {
                "price_start": [pd.Timestamp("2025-01-01 00:00:00", tz="UTC")],
                "price_end": [pd.Timestamp("2025-01-01 01:00:00", tz="UTC")],
                "marketprice_eur_per_kwh": [0.1],
            }
        )

        synchronized = synchronize_consumption_and_price(consumption, price)

        self.assertEqual(
            list(synchronized.columns),
            [
                "datetime_start",
                "datetime_end",
                "consumption_kwh",
                "marketprice_eur_per_kwh",
            ],
        )
        self.assertEqual(len(synchronized), 4)


if __name__ == "__main__":
    unittest.main()

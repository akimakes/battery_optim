import unittest

import pandas as pd

from batt.data_io import filter_latest_days


class DataIoTests(unittest.TestCase):
    def test_full_time_range_returns_all_rows(self):
        df = self.interval_df(days=3)

        result = filter_latest_days(df, "full")

        self.assertEqual(len(result), len(df))

    def test_numeric_time_range_returns_latest_days(self):
        df = self.interval_df(days=3)

        result = filter_latest_days(df, 1)

        self.assertEqual(len(result), 96)
        self.assertEqual(result["datetime_end"].max(), df["datetime_end"].max())

    def test_invalid_time_range_raises(self):
        df = self.interval_df(days=1)

        with self.assertRaises(ValueError):
            filter_latest_days(df, 0)

    @staticmethod
    def interval_df(days: int) -> pd.DataFrame:
        periods = days * 96
        starts = pd.date_range("2024-01-01", periods=periods, freq="15min", tz="UTC")
        return pd.DataFrame(
            {
                "datetime_start": starts,
                "datetime_end": starts + pd.Timedelta(minutes=15),
                "consumption_kwh": [0.1] * periods,
                "marketprice_eur_per_kwh": [0.1] * periods,
            }
        )


if __name__ == "__main__":
    unittest.main()

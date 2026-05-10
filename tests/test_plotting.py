import unittest

import pandas as pd

from batt.plotting import PlotConfig, filter_plot_month


class PlottingTests(unittest.TestCase):
    def test_filter_plot_month_uses_configured_timezone(self):
        df = pd.DataFrame(
            {
                "datetime_start": pd.to_datetime(
                    [
                        "2025-01-31 22:45:00+00:00",
                        "2025-01-31 23:00:00+00:00",
                    ],
                    utc=True,
                ),
                "datetime_end": pd.to_datetime(
                    [
                        "2025-01-31 23:00:00+00:00",
                        "2025-01-31 23:15:00+00:00",
                    ],
                    utc=True,
                ),
            }
        )
        config = PlotConfig(
            enabled=True,
            year=2025,
            month=2,
            timezone="Europe/Vienna",
            output_file="unused.png",
        )

        result = filter_plot_month(df, config)

        self.assertEqual(len(result), 1)
        self.assertEqual(result["plot_datetime"].iloc[0].month, 2)

    def test_invalid_month_raises(self):
        df = pd.DataFrame()
        config = PlotConfig(
            enabled=True,
            year=2025,
            month=13,
            timezone="Europe/Vienna",
            output_file="unused.png",
        )

        with self.assertRaises(ValueError):
            filter_plot_month(df, config)


if __name__ == "__main__":
    unittest.main()

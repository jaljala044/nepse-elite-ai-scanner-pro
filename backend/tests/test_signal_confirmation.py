import unittest
from datetime import date, timedelta
from app.signal_confirmation import confirm_signal


def rising_rows(count=60):
    start = date(2025, 1, 1)
    rows = []
    for i in range(count):
        close = 100 + i
        rows.append({"date": start + timedelta(days=i), "open": close - 1,
                     "high": close + 1, "low": close - 2,
                     "close": close, "volume": 1000})
    return rows


def declining_rows(count=60):
    start = date(2025, 1, 1)
    rows = []
    for i in range(count):
        close = 160 - i
        rows.append({"date": start + timedelta(days=i), "open": close + 1,
                     "high": close + 2, "low": close - 2,
                     "close": close, "volume": 1000})
    return rows


class SignalConfirmationTests(unittest.TestCase):
    def test_blocks_unreviewed_data(self):
        result = confirm_signal(rising_rows(), eligible=False)
        self.assertEqual(result["classification"], "UNKNOWN")
        self.assertEqual(result["status"], "unknown")

    def test_insufficient_history_is_unknown(self):
        result = confirm_signal(rising_rows(30), eligible=True)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["classification"], "UNKNOWN")

    def test_bullish_breakout_confirmation_is_research_only(self):
        rows = rising_rows()
        rows[-1].update(open=159, high=165, low=158, close=164, volume=2500)
        result = confirm_signal(rows, eligible=True)
        self.assertEqual(result["classification"], "bullish_confirmation")
        self.assertEqual(result["status"], "research_confirmed")
        self.assertNotIn("recommendation", result)
        self.assertNotIn("probability", result)

    def test_bearish_breakdown_requires_strictly_below_both_averages(self):
        rows = declining_rows()
        rows[-1].update(open=100, high=103, low=98, close=99, volume=2500)
        result = confirm_signal(rows, eligible=True)
        self.assertEqual(result["classification"], "bearish_warning")
        self.assertTrue(result["checks"]["breakdown_below_prior_low"])
        self.assertTrue(result["checks"]["close_below_sma20"])
        self.assertTrue(result["checks"]["close_below_sma50"])
        self.assertTrue(result["checks"]["sma20_below_sma50"])

    def test_failed_volume_prevents_confirmation(self):
        rows = rising_rows()
        rows[-1].update(open=159, high=165, low=158, close=164, volume=1000)
        result = confirm_signal(rows, eligible=True)
        self.assertEqual(result["classification"], "no_confirmation")

    def test_official_history_fields_without_open_are_supported(self):
        rows = rising_rows()
        for row in rows:
            row.pop("open")
        rows[-1].update(high=165, low=158, close=164, volume=2500)
        result = confirm_signal(rows, eligible=True)
        self.assertEqual(result["classification"], "bullish_confirmation")
        self.assertEqual(result["status"], "research_confirmed")

    def test_invalid_ohlcv_is_unknown(self):
        rows = rising_rows()
        rows[-1]["high"] = 1
        result = confirm_signal(rows, eligible=True)
        self.assertEqual(result["classification"], "UNKNOWN")

    def test_invalid_configuration_is_rejected_consistently(self):
        invalid_options = [
            {"min_observations": True},
            {"min_observations": 50},
            {"breakout_lookback": True},
            {"breakout_lookback": 4},
            {"volume_multiple": True},
            {"volume_multiple": 0},
            {"volume_multiple": float("nan")},
            {"volume_multiple": float("inf")},
            {"volume_multiple": None},
            {"volume_multiple": "1.5"},
        ]
        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    confirm_signal(rising_rows(), eligible=True, **options)

    def test_rows_are_sorted_before_pattern_evaluation(self):
        rows = rising_rows()
        rows[-1].update(open=159, high=165, low=158, close=164, volume=2500)
        shuffled = rows[::2] + rows[1::2]
        result = confirm_signal(shuffled, eligible=True)
        self.assertEqual(result["as_of"], str(rows[-1]["date"]))
        self.assertEqual(result["classification"], "bullish_confirmation")


if __name__ == "__main__":
    unittest.main()

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

    def test_failed_volume_prevents_confirmation(self):
        rows = rising_rows()
        rows[-1].update(open=159, high=165, low=158, close=164, volume=1000)
        result = confirm_signal(rows, eligible=True)
        self.assertEqual(result["classification"], "no_confirmation")

    def test_invalid_ohlcv_is_unknown(self):
        rows = rising_rows()
        rows[-1]["high"] = 1
        result = confirm_signal(rows, eligible=True)
        self.assertEqual(result["classification"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

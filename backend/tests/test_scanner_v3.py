import unittest
from datetime import date, timedelta

from app.scanner_v3 import analyze_v3


def bars(count=60):
    start = date(2025, 1, 1)
    result = []
    for i in range(count):
        close = 100 + i
        result.append({
            "date": (start + timedelta(days=i)).isoformat(),
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000 + i * 10,
        })
    return result


class ScannerV3Tests(unittest.TestCase):
    def test_returns_features_for_valid_history(self):
        result = analyze_v3("abc", bars())
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["engine"], "v3")
        self.assertEqual(result["symbol"], "ABC")
        self.assertEqual(result["metrics"]["sma20"], 149.5)
        self.assertEqual(result["metrics"]["sma50"], 134.5)
        self.assertIn("positive_20_session_return", result["evidence"])

    def test_short_history_is_explicitly_insufficient(self):
        result = analyze_v3("ABC", bars(30))
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["metrics"], {})

    def test_duplicate_dates_are_rejected(self):
        data = bars()
        data.append(data[-1].copy())
        result = analyze_v3("ABC", data)
        self.assertEqual(result["status"], "data_quality_error")
        self.assertIn("duplicate session dates detected", result["data_quality_errors"])

    def test_invalid_ohlc_is_rejected_without_repair(self):
        data = bars()
        data[10]["high"] = data[10]["close"] - 5
        result = analyze_v3("ABC", data)
        self.assertEqual(result["status"], "data_quality_error")
        self.assertTrue(any("high is below" in error for error in result["data_quality_errors"]))

    def test_zero_volume_does_not_create_infinite_ratio(self):
        data = bars()
        for row in data[-20:]:
            row["volume"] = 0
        result = analyze_v3("ABC", data)
        self.assertEqual(result["status"], "ready")
        self.assertIsNone(result["metrics"]["volume_ratio20"])

    def test_flat_price_rsi_is_neutral(self):
        data = bars()
        for row in data:
            row.update(open=100, high=101, low=99, close=100)
        result = analyze_v3("ABC", data)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["metrics"]["rsi14"], 50.0)


if __name__ == "__main__":
    unittest.main()

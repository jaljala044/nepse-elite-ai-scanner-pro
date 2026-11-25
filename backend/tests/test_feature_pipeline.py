import unittest
from app.feature_pipeline import build_feature_snapshot


class FeaturePipelineTests(unittest.TestCase):
    def test_future_rows_are_excluded_before_feature_calculation(self):
        rows = [
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-23",
             "available_at":"2026-11-23T16:00:00Z","close":11,"previous_close":10,"volume":100},
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-24",
             "available_at":"2026-11-25T16:00:00Z","close":99,"previous_close":11,"volume":9999},
            {"record_type":"broker","available_at":"2026-11-23T16:00:00Z",
             "identity_status":"unmapped","amount":500,"side":"buy"},
        ]
        result = build_feature_snapshot(rows, "2026-11-24T12:00:00Z", ["AAA","BBB"])
        self.assertEqual(result["excluded_input_count"], 1)
        self.assertEqual(result["security_features"]["AAA"]["close"], 11)
        self.assertEqual(result["market_breadth"]["observed_symbols"], 1)
        self.assertTrue(result["point_in_time_eligible"])
        self.assertEqual(result["interpretation"], "descriptive_only_not_a_trading_signal")


if __name__ == "__main__":
    unittest.main()

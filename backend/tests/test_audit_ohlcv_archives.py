import unittest

from audit_ohlcv_archives import audit_ohlcv_csv


class AuditOhlcvCsvTests(unittest.TestCase):
    def test_numeric_formatting_is_normalized_and_consecutive_repeat_is_flagged(self):
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "2024-01-02,10.00,11.0,9.00,10.50,100.0\n"
            "2024-01-03,10,11,9,10.5,100\n"
        ).encode()
        result = audit_ohlcv_csv(content, "03_stock_charts_ohlcv/TEST_OHLCV.csv")
        self.assertEqual(result["valid_rows"], 2)
        self.assertEqual(result["unique_dates"], 2)
        self.assertEqual(result["invalid_rows"], [])
        self.assertEqual(result["repeated_adjacent_calendar_rows"], 1)
        self.assertEqual(result["observations"]["2024-01-02"][0]["volume"], "100")

    def test_duplicate_date_and_out_of_order_are_detected(self):
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "2024-01-03,10,11,9,10,100\n"
            "2024-01-03,10,11,9,10,100\n"
            "2024-01-02,10,11,9,10,100\n"
        ).encode()
        result = audit_ohlcv_csv(content, "TEST_OHLCV.csv")
        self.assertEqual(result["duplicate_dates"], [{"date": "2024-01-03", "count": 2}])
        self.assertEqual(result["out_of_order_transitions"], 1)

    def test_invalid_ohlc_and_non_integer_volume_are_rejected(self):
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "2024-01-02,10,9,8,10,100\n"
            "2024-01-03,10,11,9,10,100.5\n"
        ).encode()
        result = audit_ohlcv_csv(content, "TEST_OHLCV.csv")
        self.assertEqual(result["valid_rows"], 0)
        self.assertEqual(len(result["invalid_rows"]), 2)

    def test_missing_required_column_fails_closed(self):
        content = b"Date,Open,High,Low,Close\n2024-01-02,10,11,9,10\n"
        with self.assertRaises(ValueError):
            audit_ohlcv_csv(content, "TEST_OHLCV.csv")


if __name__ == "__main__":
    unittest.main()

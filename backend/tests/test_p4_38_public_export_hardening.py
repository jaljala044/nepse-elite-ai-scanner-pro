import unittest
from app.p4_38_public_export_intake import normalize_ohlcv_rows, normalize_close_only_rows, normalize_floorsheet_rows, parse_csv_bytes

class PublicExportHardeningTests(unittest.TestCase):
    def test_ltp_is_not_an_ohlcv_close_fallback(self):
        row = {"date": "2026-11-27", "open": 99, "high": 101, "low": 98, "ltp": 100, "volume": 1000}
        result = normalize_ohlcv_rows(provider="sharehub", symbol="BENH", rows=[row])
        self.assertEqual(result["records"], [])
        self.assertIn("missing_ohlcv_field", result["rejected"][0]["reason"])

    def test_non_finite_ohlcv_is_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            row = {"date": "2026-11-27", "open": 99, "high": 101, "low": 98, "close": value, "volume": 1000}
            result = normalize_ohlcv_rows(provider="sharehub", symbol="BENH", rows=[row])
            self.assertEqual(result["records"], [])
            self.assertEqual(result["rejected"][0]["reason"], "non_finite_ohlcv_value")

    def test_malformed_date_suffix_is_rejected(self):
        row = {"date": "2026-11-27garbage", "open": 99, "high": 101, "low": 98, "close": 100, "volume": 1000}
        result = normalize_ohlcv_rows(provider="sharehub", symbol="BENH", rows=[row])
        self.assertEqual(result["records"], [])

    def test_non_finite_close_only_is_rejected(self):
        result = normalize_close_only_rows(provider="public", symbol="BENH", rows=[{"date": "2026-11-27", "close": float("nan")}])
        self.assertEqual(result["records"], [])

    def test_non_finite_floorsheet_values_are_rejected(self):
        result = normalize_floorsheet_rows(symbol="BENH", rows=[{"date": "2026-11-27", "symbol": "BENH", "qty": float("inf"), "rate": 100}])
        self.assertEqual(result["records"], [])
        self.assertEqual(result["rejected"][0]["reason"], "non_finite_quantity_or_price")

    def test_extra_csv_field_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_csv_bytes(b"date,close\n2026-11-27,10,extra\n")

    def test_duplicate_session_quarantines_both_rows_and_removes_candidate(self):
        rows = [
            {"date": "2026-11-27", "open": 99, "high": 101, "low": 98, "close": 100, "volume": 1000},
            {"date": "2026-11-27", "open": 99, "high": 102, "low": 98, "close": 101, "volume": 1100},
        ]
        result = normalize_ohlcv_rows(provider="sharehub", symbol="BENH", rows=rows)
        self.assertEqual(result["records"], [])
        self.assertEqual(
            [(item["row_index"], item["reason"]) for item in result["rejected"]],
            [(0, "duplicate_symbol_session"), (1, "duplicate_symbol_session")],
        )

if __name__ == "__main__":
    unittest.main()

import unittest
from app.ohlcv_csv_adapter import OhlcvCsvMapping, parse_ohlcv_csv


MAPPING = OhlcvCsvMapping({
    "symbol": "Ticker", "session_date": "Date", "open": "Open",
    "high": "High", "low": "Low", "close": "Close", "volume": "Volume",
})


class OhlcvCsvAdapterTests(unittest.TestCase):
    def payload(self, row):
        return ("Ticker,Date,Open,High,Low,Close,Volume\n" + row + "\n").encode()

    def test_valid_row_parsed_with_exact_lineage(self):
        result = parse_ohlcv_csv(self.payload("NABIL,2026-11-24,100,110,95,105,1000"),
                                 source_id="fixture", mapping=MAPPING)
        self.assertEqual(result["parsed_rows"], 1)
        self.assertEqual(result["rows"][0]["source_row_number"], 2)
        self.assertEqual(result["rows"][0]["status"], "parsed_review_required")
        self.assertFalse(result["promotion_allowed"])

    def test_invalid_high_low_bounds_quarantined_not_dropped(self):
        result = parse_ohlcv_csv(self.payload("NABIL,2026-11-24,100,90,95,105,1000"),
                                 source_id="fixture", mapping=MAPPING)
        self.assertEqual(result["parsed_rows"], 1)
        self.assertIn("high_bound_violation", result["rows"][0]["exception_flags"])
        self.assertEqual(result["exception_rows"], 1)

    def test_malformed_numeric_retained_as_rejected_exception(self):
        result = parse_ohlcv_csv(self.payload("NABIL,2026-11-24,bad,110,95,105,1000"),
                                 source_id="fixture", mapping=MAPPING)
        self.assertEqual(result["parsed_rows"], 0)
        self.assertEqual(result["exceptions"][0]["source_row_number"], 2)

    def test_zero_volume_is_allowed_for_a_verified_session_row(self):
        result = parse_ohlcv_csv(self.payload("NABIL,2026-11-24,100,110,95,105,0"),
                                 source_id="fixture", mapping=MAPPING)
        self.assertEqual(result["parsed_rows"], 1)
        self.assertEqual(result["rows"][0]["volume"], "0")

    def test_missing_mapped_header_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "mapped OHLCV headers absent"):
            parse_ohlcv_csv(b"Date,Ticker\n2026-11-24,NABIL\n",
                            source_id="fixture", mapping=MAPPING)

    def test_duplicate_header_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate OHLCV"):
            parse_ohlcv_csv(b"Ticker,Date,Open,High,Low,Close,Volume,Volume\n",
                            source_id="fixture", mapping=MAPPING)


if __name__ == "__main__":
    unittest.main()

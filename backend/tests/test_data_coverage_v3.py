import unittest
from datetime import date

from app.data_coverage_v3 import audit_ohlcv


def row(symbol, day, close=100):
    return {"symbol": symbol, "date": day, "open": close, "high": close + 1,
            "low": close - 1, "close": close, "volume": 1000}


class DataCoverageV3Tests(unittest.TestCase):
    def test_exact_universe_and_missing_symbol(self):
        report = audit_ohlcv([row("AAA", "2026-01-01")], expected_symbols=["AAA", "BBB"])
        self.assertEqual(report["observed_symbols"], 1)
        self.assertEqual(report["missing_symbols"], ["BBB"])
        self.assertEqual(report["per_symbol"][1]["status"], "missing_symbol")

    def test_session_gaps_only_when_calendar_supplied(self):
        rows = [row("AAA", "2026-01-01"), row("AAA", "2026-01-05")]
        without_calendar = audit_ohlcv(rows)
        with_calendar = audit_ohlcv(
            rows, expected_sessions=["2026-01-01", "2026-01-02", "2026-01-05"],
            as_of="2026-01-05",
        )
        self.assertIsNone(without_calendar["per_symbol"][0]["calendar_sessions_missing"])
        self.assertEqual(with_calendar["per_symbol"][0]["missing_session_dates"], ["2026-01-02"])

    def test_duplicate_key_is_reported_not_double_counted(self):
        report = audit_ohlcv([row("AAA", "2026-01-01"), row("AAA", "2026-01-01")])
        self.assertEqual(report["valid_unique_rows"], 1)
        self.assertEqual(report["duplicate_keys"], 1)

    def test_invalid_ohlc_is_reported(self):
        bad = row("AAA", "2026-01-01")
        bad["high"] = 90
        report = audit_ohlcv([bad])
        self.assertEqual(report["invalid_rows"], 1)
        self.assertEqual(report["observed_symbols"], 0)

    def test_cutoff_and_staleness_are_explicit(self):
        report = audit_ohlcv([row("AAA", "2026-01-01")], as_of=date(2026, 1, 5))
        self.assertEqual(report["per_symbol"][0]["stale_calendar_days_as_of"], 4)


if __name__ == "__main__":
    unittest.main()

import unittest
from app.historical_coverage import build_historical_coverage_report


def row(source, symbol, close, day="2026-11-24"):
    return {"source_id": source, "symbol": symbol, "session_date": day, "close": close}


class HistoricalCoverageTests(unittest.TestCase):
    def test_coverage_uses_only_supplied_expected_grid(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100")],
            expected_sessions=["2026-11-24", "2026-11-25"],
            expected_symbols=["NABIL", "NICA"])
        self.assertEqual(r["expected_symbol_session_keys"], 4)
        self.assertEqual(r["source_reports"]["A"]["covered_keys"], 1)
        self.assertEqual(r["source_reports"]["A"]["coverage_ratio"], "0.25")

    def test_cross_source_disagreement_flagged_without_preference(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100"), row("B", "NABIL", "101")],
            expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(r["cross_source_close_conflict_count"], 1)
        self.assertFalse(r["canonical_promotion_allowed"])

    def test_duplicate_rows_reported(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100"), row("A", "NABIL", "100")],
            expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(len(r["source_reports"]["A"]["duplicate_keys"]), 1)

    def test_missing_session_and_symbol_not_inferred(self):
        r = build_historical_coverage_report(
            [], expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(r["union_missing_keys"], 1)
        self.assertFalse(r["unverified_weekday_inference_used"])

    def test_same_source_duplicate_difference_is_not_called_cross_source_conflict(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100"), row("A", "NABIL", "101")],
            expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(r["cross_source_close_conflict_count"], 0)
        self.assertEqual(len(r["source_reports"]["A"]["duplicate_keys"]), 1)

    def test_empty_expected_grid_rejected(self):
        with self.assertRaisesRegex(ValueError, "verified expected"):
            build_historical_coverage_report([], expected_sessions=[], expected_symbols=["NABIL"])


if __name__ == "__main__":
    unittest.main()

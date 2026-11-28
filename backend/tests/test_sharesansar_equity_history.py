import tempfile
import unittest
from datetime import date
from pathlib import Path

from audit_sharesansar_equity_history import _git_blob_sha, classify_span, load_crosswalk, summarize_payload


class ShareSansarEquityHistoryCoverageTests(unittest.TestCase):
    def test_git_blob_sha_uses_git_object_header(self):
        self.assertEqual(_git_blob_sha(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_three_and_five_year_thresholds_are_calendar_based(self):
        three = classify_span(date(2021, 3, 1), date(2024, 3, 1))
        five = classify_span(date(2021, 3, 1), date(2026, 3, 1))
        self.assertTrue(three["meets_3_years"])
        self.assertFalse(three["meets_5_years"])
        self.assertTrue(five["meets_3_years"])
        self.assertTrue(five["meets_5_years"])

    def test_leap_day_anniversary_uses_february_28(self):
        result = classify_span(date(2020, 2, 29), date(2023, 2, 28))
        self.assertTrue(result["meets_3_years"])

    def test_payload_reports_bounds_and_malformed_rows_without_inventing_dates(self):
        result = summarize_payload([
            {"d": "2024-03-04", "o": 1}, {"d": "2026-11-27", "o": 2},
            {"d": "not-a-date"}, None,
        ])
        self.assertEqual(result["row_count"], 4)
        self.assertEqual(result["dated_row_count"], 2)
        self.assertEqual(result["malformed_date_or_row_count"], 2)
        self.assertEqual(result["first_date"], "2024-03-04")
        self.assertEqual(result["last_date"], "2026-11-27")
        self.assertFalse(result["meets_3_years"])

    def test_columnar_archive_payload_parses_date_column(self):
        result = summarize_payload({
            "symbol": "ABC", "cols": ["d", "o", "h", "l", "c", "vol"],
            "rows": [["2024-03-04", 1, 2, 1, 2, 10], ["2026-11-27", 2, 3, 2, 3, 20]],
        }, expected_symbol="ABC")
        self.assertEqual(result["schema_layout"], "columnar_object")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["first_date"], "2024-03-04")
        self.assertEqual(result["last_date"], "2026-11-27")
        self.assertFalse(result["meets_3_years"])

    def test_payload_symbol_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            summarize_payload({
                "symbol": "XYZ", "cols": ["d", "o"], "rows": [["2024-01-01", 1]],
            }, expected_symbol="ABC")

    def test_invalid_payload_shape_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "columnar history payload"):
            summarize_payload({"data": []})

    def test_missing_date_bounds_do_not_qualify(self):
        result = classify_span(None, None)
        self.assertIsNone(result["calendar_days"])
        self.assertFalse(result["meets_3_years"])

    def test_crosswalk_requires_exact_unique_universe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "crosswalk.csv"
            path.write_text(
                "symbol,security_id,snapshot_date,active_status,crosswalk_status\n"
                "ABC,1,2026-11-25,A,match\nXYZ,2,2026-11-25,A,match\n",
                encoding="utf-8",
            )
            rows = load_crosswalk(path, expected_count=2)
            self.assertEqual([row["symbol"] for row in rows], ["ABC", "XYZ"])
            with self.assertRaisesRegex(ValueError, "expected 3"):
                load_crosswalk(path, expected_count=3)


if __name__ == "__main__":
    unittest.main()

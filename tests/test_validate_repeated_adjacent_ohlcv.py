import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_repeated_adjacent_ohlcv import validate_candidate_ledger


class CandidateLedgerIntegrityTests(unittest.TestCase):
    HEADER = [
        "repository", "commit_sha", "path", "file_sha256", "symbol",
        "previous_date", "current_date", "previous_csv_line", "current_csv_line",
        "ohlcv", "classification",
    ]

    def write_ledger(self, root: Path, rows):
        path = root / "candidates.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.HEADER)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def row(self, **overrides):
        value = {
            "repository": "owner/repo",
            "commit_sha": "a" * 40,
            "path": "03_stock_charts_ohlcv/ABC_OHLCV.csv",
            "file_sha256": "b" * 64,
            "symbol": "ABC",
            "previous_date": "2026-01-01",
            "current_date": "2026-01-02",
            "previous_csv_line": "2",
            "current_csv_line": "3",
            "ohlcv": json.dumps({"Open": "10", "High": "11", "Low": "9", "Close": "10", "Volume": "100"}),
            "classification": "calendar_status_unverified_review_flag",
        }
        value.update(overrides)
        return value

    def test_valid_candidate_is_structurally_clean_but_never_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_candidate_ledger(self.write_ledger(Path(tmp), [self.row()]))
        self.assertEqual(report["candidate_rows"], 1)
        self.assertEqual(report["structural_findings"], 0)
        self.assertFalse(report["source_data_modified"])
        self.assertFalse(report["canonical_promotion_allowed"])

    def test_duplicate_identity_and_non_adjacent_source_lines_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = self.row(current_csv_line="4")
            report = validate_candidate_ledger(self.write_ledger(Path(tmp), [row, row]))
        self.assertEqual(report["finding_counts"]["NON_ADJACENT_SOURCE_LINES"], 2)
        self.assertEqual(report["finding_counts"]["DUPLICATE_SOURCE_OCCURRENCE"], 1)

    def test_duplicate_and_out_of_order_dates_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [
                self.row(previous_date="2026-01-02", current_date="2026-01-02"),
                self.row(previous_date="2026-01-03", current_date="2026-01-02",
                         previous_csv_line="4", current_csv_line="5"),
            ]
            report = validate_candidate_ledger(self.write_ledger(Path(tmp), rows))
        self.assertEqual(report["finding_counts"]["DUPLICATE_ADJACENT_DATE"], 1)
        self.assertEqual(report["finding_counts"]["OUT_OF_ORDER_DATE"], 1)

    def test_invalid_ohlc_and_malformed_dates_are_flagged_without_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = self.row(
                previous_date="2026-02-30",
                ohlcv=json.dumps({"Open": "12", "High": "11", "Low": "9", "Close": "10", "Volume": "100"}),
            )
            report = validate_candidate_ledger(self.write_ledger(Path(tmp), [row]))
        self.assertEqual(report["finding_counts"]["MALFORMED_DATE"], 1)
        self.assertEqual(report["finding_counts"]["INVALID_OHLC_BOUNDS"], 1)
        self.assertFalse(report["canonical_promotion_allowed"])

    def test_missing_required_columns_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("symbol,date\\nABC,2026-01-01\\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing columns"):
                validate_candidate_ledger(path)


if __name__ == "__main__":
    unittest.main()

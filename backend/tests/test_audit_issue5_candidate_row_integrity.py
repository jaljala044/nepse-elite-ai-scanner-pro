import csv
import json
import tempfile
import unittest
from pathlib import Path

from audit_issue5_candidate_row_integrity import audit


FIELDS = [
    "repository", "commit_sha", "path", "file_sha256", "symbol",
    "previous_date", "current_date", "previous_csv_line", "current_csv_line",
    "ohlcv", "classification", "review_reason",
]


def row(**overrides):
    value = {
        "repository": "owner/repo", "commit_sha": "a" * 40,
        "path": "ABC.csv", "file_sha256": "b" * 64, "symbol": "ABC",
        "previous_date": "2026-01-01", "current_date": "2026-01-02",
        "previous_csv_line": "2", "current_csv_line": "3",
        "ohlcv": json.dumps({
            "Open": "10", "High": "12", "Low": "9",
            "Close": "11", "Volume": "100",
        }),
        "classification": "calendar_status_unverified_review_flag",
        "review_reason": "fixture",
    }
    value.update(overrides)
    return value


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class Issue5CandidateIntegrityTests(unittest.TestCase):
    def test_clean_candidate_extract_passes_structural_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row()])
            report = audit(path)
            self.assertEqual(report["candidate_rows"], 1)
            self.assertEqual(report["invalid_current_ohlc"], [])
            self.assertEqual(report["duplicate_candidate_pair_keys"], [])
            self.assertEqual(report["missing_source_rows"]["status"], "NOT_ASSESSED")

    def test_invalid_ohlc_is_reported_without_mutation(self):
        invalid = json.dumps({
            "Open": "13", "High": "12", "Low": "9",
            "Close": "11", "Volume": "100",
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(ohlcv=invalid)])
            report = audit(path)
            self.assertEqual(len(report["invalid_current_ohlc"]), 1)
            self.assertFalse(report["raw_source_values_modified"])

    def test_duplicate_candidate_date_and_pair_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(), row()])
            report = audit(path)
            self.assertEqual(len(report["duplicate_repository_symbol_current_date_keys"]), 1)
            self.assertEqual(len(report["duplicate_candidate_pair_keys"]), 1)

    def test_noncanonical_or_reversed_dates_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(previous_date="2026-01-03", current_date="2026-01-02")])
            self.assertEqual(len(audit(path)["invalid_date_order"]), 1)

    def test_candidate_line_order_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [
                row(previous_csv_line="2", current_csv_line="3"),
                row(previous_date="2026-01-02", current_date="2026-01-03",
                    previous_csv_line="4", current_csv_line="5"),
                row(previous_date="2026-01-03", current_date="2026-01-04",
                    previous_csv_line="3", current_csv_line="6"),
            ])
            self.assertEqual(len(audit(path)["source_candidate_order_violations"]), 1)

    def test_non_review_classification_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(classification="accepted")])
            self.assertEqual(len(audit(path)["non_review_only_classifications"]), 1)


if __name__ == "__main__":
    unittest.main()

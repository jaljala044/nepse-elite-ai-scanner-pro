import csv
import tempfile
import unittest
from pathlib import Path

from scripts.summarize_issue5_cross_source_gap_overlap import summarize, write_report

FIELDS = [
    "repository", "symbol", "trade_date", "gap_status",
    "canonical_promotion_allowed", "raw_source_modified",
]
SMC = "jaljala044/nepse-smc-data"
HISTORY = "jaljala044/nepse-history-starter"
STATUS = "UNCLASSIFIED_NO_TRADE_OR_MISSING_OR_LIFECYCLE"


class Issue5CrossSourceGapOverlapTests(unittest.TestCase):
    def row(self, repository, symbol, day):
        return {
            "repository": repository, "symbol": symbol, "trade_date": day,
            "gap_status": STATUS, "canonical_promotion_allowed": "false",
            "raw_source_modified": "false",
        }

    def write(self, root, rows):
        path = root / "gaps.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_overlap_counts_and_no_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write(root, [
                self.row(SMC, "ABC", "2026-01-02"),
                self.row(HISTORY, "ABC", "2026-01-02"),
                self.row(SMC, "ABC", "2026-01-03"),
                self.row(HISTORY, "XYZ", "2026-01-04"),
            ])
            report = summarize(path)
            self.assertEqual(report["source_gap_rows"], 4)
            self.assertEqual(report["unique_symbol_date_keys"], 3)
            self.assertEqual(report["overlap_classification_counts"], {
                "both_sources_gap": 1,
                "history_starter_only_gap": 1,
                "smc_only_gap": 1,
            })
            self.assertFalse(report["gap_adjudication_complete"])
            self.assertFalse(report["canonical_or_training_promotion"])
            out = root / "out"
            write_report(report, out)
            self.assertTrue((out / "issue5_cross_source_gap_pair_classification.csv").exists())

    def test_duplicate_repository_symbol_date_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.row(SMC, "ABC", "2026-01-02")
            with self.assertRaisesRegex(ValueError, "duplicate repository/symbol/date"):
                summarize(self.write(root, [row, row]))

    def test_noncanonical_date_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "invalid trade date"):
                summarize(self.write(root, [self.row(SMC, "ABC", "2026-1-2")]))

    def test_unknown_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "unknown repository"):
                summarize(self.write(root, [self.row("unknown/repo", "ABC", "2026-01-02")]))

    def test_promotion_or_mutation_flag_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.row(SMC, "ABC", "2026-01-02")
            row["canonical_promotion_allowed"] = "true"
            with self.assertRaisesRegex(ValueError, "promotion flag must be false"):
                summarize(self.write(root, [row]))


if __name__ == "__main__":
    unittest.main()

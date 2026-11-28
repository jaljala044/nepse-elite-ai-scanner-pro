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


    def test_empty_gap_inventory_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "must contain at least one row"):
                summarize(self.write(root, []))


    def test_date_ranking_counts_unique_symbols_not_source_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = summarize(self.write(root, [
                self.row(SMC, "ABC", "2026-01-02"),
                self.row(HISTORY, "ABC", "2026-01-02"),
                self.row(SMC, "XYZ", "2026-01-02"),
            ]))
            self.assertEqual(report["top_dates"][0]["unique_symbol_gaps"], 2)
            self.assertEqual(report["top_dates"][0]["smc_symbol_gaps"], 2)
            self.assertEqual(report["top_dates"][0]["history_starter_symbol_gaps"], 1)
            self.assertEqual(report["top_dates"][0]["both_source_symbol_gaps"], 1)


    def test_blank_symbol_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write(root, [self.row(SMC, "ABC", "2026-01-02")])
            text = path.read_text(encoding="utf-8").replace("ABC", "")
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "symbol must be a non-empty string"):
                summarize(path)

    def test_blank_repository_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "repository must be a non-empty string"):
                summarize(self.write(root, [self.row("", "ABC", "2026-01-02")]))

    def test_blank_gap_status_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.row(SMC, "ABC", "2026-01-02")
            row["gap_status"] = ""
            with self.assertRaisesRegex(ValueError, "gap_status must be a non-empty string"):
                summarize(self.write(root, [row]))

    def test_blank_promotion_flag_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.row(SMC, "ABC", "2026-01-02")
            row["canonical_promotion_allowed"] = ""
            with self.assertRaisesRegex(ValueError, "canonical_promotion_allowed must be a non-empty string"):
                summarize(self.write(root, [row]))

    def test_blank_mutation_flag_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.row(SMC, "ABC", "2026-01-02")
            row["raw_source_modified"] = ""
            with self.assertRaisesRegex(ValueError, "raw_source_modified must be a non-empty string"):
                summarize(self.write(root, [row]))

    def test_duplicate_headers_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gaps.csv"
            path.write_text(
                "repository,symbol,symbol,trade_date,gap_status,canonical_promotion_allowed,raw_source_modified\\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate column headers"):
                summarize(path)

    def test_extra_csv_fields_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gaps.csv"
            path.write_text(
                ",".join(FIELDS) + "\\n" +
                ",".join([SMC, "ABC", "2026-01-02", STATUS, "false", "false", "unexpected"]) + "\\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unexpected extra CSV fields"):
                summarize(path)

    def test_missing_csv_field_value_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gaps.csv"
            path.write_text(
                ",".join(FIELDS) + "\\n" +
                ",".join([SMC, "ABC", "2026-01-02", STATUS, "false"]) + "\\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "raw_source_modified must be a non-empty string"):
                summarize(path)

    def test_symbol_normalization_is_case_insensitive_and_trimmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = summarize(self.write(root, [self.row(SMC, " abc ", "2026-01-02")]))
            self.assertEqual(report["top_symbols"][0]["symbol"], "ABC")

    def test_symbol_ranking_counts_each_source_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = summarize(self.write(root, [
                self.row(SMC, "ABC", "2026-01-02"),
                self.row(HISTORY, "ABC", "2026-01-02"),
                self.row(SMC, "ABC", "2026-01-03"),
            ]))
            self.assertEqual(report["top_symbols"][0]["unique_gap_dates"], 2)
            self.assertEqual(report["top_symbols"][0]["smc_gap_dates"], 2)
            self.assertEqual(report["top_symbols"][0]["history_starter_gap_dates"], 1)
            self.assertEqual(report["top_symbols"][0]["both_source_gap_dates"], 1)


    def test_raw_source_mutation_flag_true_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.row(SMC, "ABC", "2026-01-02")
            row["raw_source_modified"] = "true"
            with self.assertRaisesRegex(ValueError, "raw-source mutation flag must be false"):
                summarize(self.write(root, [row]))


if __name__ == "__main__":
    unittest.main()

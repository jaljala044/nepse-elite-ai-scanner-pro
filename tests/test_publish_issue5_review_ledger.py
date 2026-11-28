import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publish_issue5_review_ledger.py"
SPEC = importlib.util.spec_from_file_location("publish_issue5_review_ledger", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class PublishIssue5ReviewLedgerTests(unittest.TestCase):
    def test_deterministic_output_and_fail_closed_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            fields = ["repository","commit_sha","path","file_sha256","symbol",
                      "previous_date","current_date","previous_csv_line","current_csv_line",
                      "calendar_day_gap","ohlc_bounds_valid"]
            rows = [
                ["jaljala044/nepse-smc-data","937cfcf93d78dfcf28a9f09bb13291447988157b","x.csv","b"*64,"AAA","2024-01-01","2024-01-02","2","3","1","True"],
                ["jaljala044/nepse-smc-data","937cfcf93d78dfcf28a9f09bb13291447988157b","x.csv","b"*64,"AAA","2024-01-03","2024-01-06","4","5","3","True"],
                ["jaljala044/nepse-history-starter","b60728d39f34e0f9e428675d817fd52ed2784da6","y.csv","d"*64,"BBB","2024-01-01","2024-01-02","2","3","1","False"],
            ]
            with source.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f); writer.writerow(fields); writer.writerows(rows)
            out1, out2 = root / "one.csv", root / "two.csv"
            manifest1 = MODULE.build(source, out1)
            manifest2 = MODULE.build(source, out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())
            self.assertEqual(manifest1["output_sha256"], manifest2["output_sha256"])
            self.assertEqual(manifest1["counts"]["candidate_rows"], 3)
            self.assertEqual(manifest1["counts"]["invalid_ohlc_geometry"], 1)
            self.assertEqual(manifest1["counts"]["multi_day_date_gap"], 1)
            self.assertFalse(manifest1["counts"]["canonical_promotion_allowed"])

    def test_duplicate_source_occurrence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "input.csv"
            fields = ["repository","commit_sha","path","file_sha256","symbol",
                      "previous_date","current_date","previous_csv_line","current_csv_line",
                      "calendar_day_gap","ohlc_bounds_valid"]
            row = ["jaljala044/nepse-smc-data","937cfcf93d78dfcf28a9f09bb13291447988157b","x.csv","b"*64,"AAA","2024-01-01","2024-01-02","2","3","1","True"]
            with source.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f); writer.writerow(fields); writer.writerow(row); writer.writerow(row)
            with self.assertRaises(ValueError):
                MODULE.build(source, root / "out.csv")


    def test_unknown_repository_and_unapproved_commit_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            fields = ["repository","commit_sha","path","file_sha256","symbol",
                      "previous_date","current_date","previous_csv_line","current_csv_line",
                      "calendar_day_gap","ohlc_bounds_valid"]
            row = ["unknown/repo","a"*40,"x.csv","b"*64,"AAA",
                   "2024-01-01","2024-01-02","2","3","1","True"]
            with source.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f); writer.writerow(fields); writer.writerow(row)
            with self.assertRaisesRegex(ValueError, "unknown candidate repository"):
                MODULE.build(source, root / "out.csv")

    def test_noncanonical_dates_and_invalid_line_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            fields = ["repository","commit_sha","path","file_sha256","symbol",
                      "previous_date","current_date","previous_csv_line","current_csv_line",
                      "calendar_day_gap","ohlc_bounds_valid"]
            row = ["jaljala044/nepse-smc-data","937cfcf93d78dfcf28a9f09bb13291447988157b",
                   "x.csv","b"*64,"AAA","2024-1-1","2024-01-02","2","3","1","True"]
            with source.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f); writer.writerow(fields); writer.writerow(row)
            with self.assertRaisesRegex(ValueError, "invalid previous_date|noncanonical previous_date"):
                MODULE.build(source, root / "out.csv")


if __name__ == "__main__":
    unittest.main()

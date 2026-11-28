import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publish_issue5_review_ledger.py"
SPEC = importlib.util.spec_from_file_location("publish_issue5_review_ledger", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class PublishIssue5ReviewLedgerTests(unittest.TestCase):
    def _input(self, root):
        source = root / "input.csv"
        fields = ["repository","commit_sha","path","file_sha256","symbol",
                  "previous_date","current_date","previous_csv_line","current_csv_line",
                  "calendar_day_gap","ohlc_bounds_valid"]
        rows = [
            ["repo/a","a"*40,"x.csv","b"*64,"AAA","2024-01-01","2024-01-02","2","3","1","True"],
            ["repo/a","a"*40,"x.csv","b"*64,"AAA","2024-01-03","2024-01-06","4","5","3","True"],
            ["repo/b","c"*40,"y.csv","d"*64,"BBB","2024-01-01","2024-01-02","2","3","1","False"],
        ]
        with source.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(fields); writer.writerows(rows)
        report = root / "validator.json"
        report.write_text(json.dumps({
            "input_sha256": MODULE.sha256(source), "candidate_rows": 3,
            "unique_source_occurrences": 3, "structural_findings": 1,
            "finding_counts": {"INVALID_OHLC_BOUNDS": 1},
        }), encoding="utf-8")
        return source, report

    def test_deterministic_output_and_validator_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, report = self._input(root)
            out1, out2 = root / "one.csv", root / "two.csv"
            manifest1 = MODULE.build(source, out1, report)
            manifest2 = MODULE.build(source, out2, report)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())
            self.assertEqual(manifest1["output_sha256"], manifest2["output_sha256"])
            self.assertEqual(manifest1["counts"]["candidate_rows"], 3)
            self.assertEqual(manifest1["counts"]["invalid_ohlc_geometry"], 1)
            self.assertEqual(manifest1["counts"]["multi_day_or_unparseable_date_gap"], 1)
            self.assertFalse(manifest1["counts"]["canonical_promotion_allowed"])

    def test_unexpected_validator_findings_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, report = self._input(root)
            data = json.loads(report.read_text())
            data["structural_findings"] = 2
            data["finding_counts"]["NON_ADJACENT_SOURCE_LINES"] = 1
            report.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "unexpected structural findings"):
                MODULE.build(source, root / "out.csv", report)

    def test_validator_input_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, report = self._input(root)
            data = json.loads(report.read_text())
            data["input_sha256"] = "0" * 64
            report.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                MODULE.build(source, root / "out.csv", report)

    def test_duplicate_source_occurrence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "input.csv"
            fields = ["repository","commit_sha","path","file_sha256","symbol",
                      "previous_date","current_date","previous_csv_line","current_csv_line",
                      "calendar_day_gap","ohlc_bounds_valid"]
            row = ["repo/a","a"*40,"x.csv","b"*64,"AAA","2024-01-01","2024-01-02","2","3","1","True"]
            with source.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f); writer.writerow(fields); writer.writerow(row); writer.writerow(row)
            with self.assertRaises(ValueError):
                MODULE.build(source, root / "out.csv", root / "missing-validator.json")

if __name__ == "__main__":
    unittest.main()

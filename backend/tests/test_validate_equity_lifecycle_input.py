import csv
import tempfile
import unittest
from pathlib import Path

from validate_equity_lifecycle_input import validate_equity_lifecycle_input


class EquityLifecycleInputTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.lifecycle = self.root / "data/reference/nepse_equity_lifecycle_coverage_input_2026-11-26.csv"
        self.crosswalk = self.root / "data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv"

    def test_current_281_row_input_is_valid_but_not_promotable(self):
        report = validate_equity_lifecycle_input(self.lifecycle, self.crosswalk)
        self.assertEqual(report["status"], "valid_input_with_unverified_lifecycle", report["errors"])
        self.assertEqual(report["lifecycle_row_count"], 281)
        with self.lifecycle.open(encoding="utf-8", newline="") as source:
            input_rows = list(csv.DictReader(source))
        expected_verified = sorted(
            row["symbol"] for row in input_rows
            if row["valid_from_evidence_status"] != "unverified"
        )
        self.assertEqual(report["verified_start_count"], len(expected_verified))
        self.assertEqual(report["verified_start_symbols"], expected_verified)
        self.assertEqual(report["unverified_start_count"], 281 - len(expected_verified))
        self.assertFalse(report["promotion_allowed"])
        self.assertEqual(report["errors"], [])

    def test_verified_start_requires_date_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lifecycle.csv"
            with self.lifecycle.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["valid_from_evidence_status"] = "verified_secondary_notice"
            rows[0]["valid_from"] = ""
            rows[0]["valid_from_evidence_uri"] = ""
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            report = validate_equity_lifecycle_input(path, self.crosswalk)
            self.assertEqual(report["status"], "invalid")
            self.assertTrue(any(rows[0]["symbol"] + ":verified_start_requires_date_uri_and_note" == x
                                for x in report["errors"]))

    def test_symbol_id_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lifecycle.csv"
            with self.lifecycle.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["security_id"] = "999999"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            report = validate_equity_lifecycle_input(path, self.crosswalk)
            self.assertIn(rows[0]["symbol"] + ":security_id_does_not_match_current_crosswalk", report["errors"])

    def test_unverified_start_cannot_carry_inferred_date(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lifecycle.csv"
            with self.lifecycle.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["valid_from"] = "2010-01-01"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            report = validate_equity_lifecycle_input(path, self.crosswalk)
            self.assertIn(rows[0]["symbol"] + ":unverified_start_must_not_claim_date_or_evidence_uri",
                          report["errors"])


if __name__ == "__main__":
    unittest.main()

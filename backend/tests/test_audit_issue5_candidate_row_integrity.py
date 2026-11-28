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



    def test_invalid_commit_and_file_hashes_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(commit_sha="not-a-commit", file_sha256="bad")])
            self.assertEqual(len(audit(path)["invalid_source_file_identity"]), 1)

    def test_path_traversal_and_blank_identity_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(path="../outside.csv"), row(symbol=" ")])
            self.assertEqual(len(audit(path)["invalid_source_file_identity"]), 2)

    def test_source_rows_must_be_adjacent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(previous_csv_line="2", current_csv_line="4")])
            self.assertEqual(len(audit(path)["invalid_source_line_pairs"]), 1)

    def test_non_integer_volume_is_invalid_ohlc(self):
        values = {"Open": "10", "High": "12", "Low": "9",
                  "Close": "11", "Volume": "100.5"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(ohlcv=json.dumps(values))])
            self.assertEqual(len(audit(path)["invalid_current_ohlc"]), 1)

    def test_duplicate_ohlcv_json_keys_are_rejected(self):
        raw = '{"Open":"10","High":"12","Low":"9","Close":"11","Volume":"100","Volume":"101"}'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(ohlcv=raw)])
            self.assertEqual(len(audit(path)["invalid_current_ohlc"]), 1)

    def test_wrong_ohlcv_schema_is_rejected(self):
        values = {"Open": "10", "High": "12", "Low": "9",
                  "Close": "11", "Volume": "100", "LTP": "11"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(ohlcv=json.dumps(values))])
            self.assertEqual(len(audit(path)["invalid_current_ohlc"]), 1)

    def test_extra_or_missing_csv_fields_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row()])
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text(lines[0] + "\n" + lines[1] + ",unexpected\n", encoding="utf-8")
            self.assertEqual(len(audit(path)["malformed_csv_rows"]), 1)

    def test_duplicate_csv_headers_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            path.write_text(",".join(FIELDS + ["symbol"]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate CSV header"):
                audit(path)

    def test_cli_refuses_to_overwrite_candidate_input(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row()])
            before = path.read_bytes()
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parents[1] / "audit_issue5_candidate_row_integrity.py"),
                 "--input", str(path), "--output", str(path)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_bytes(), before)


    def test_noncanonical_source_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row(path="dir//ABC.csv"), row(path="dir/./ABC.csv")])
            self.assertEqual(len(audit(path)["invalid_source_file_identity"]), 2)

    def test_malformed_rows_remain_in_candidate_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row()])
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text(lines[0] + "\n" + lines[1] + ",extra\n", encoding="utf-8")
            report = audit(path)
            self.assertEqual(report["candidate_rows"], 1)
            self.assertEqual(report["candidate_rows_validated"], 0)
            self.assertEqual(report["candidate_rows_excluded_malformed"], 1)

    def test_short_csv_rows_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            write_csv(path, [row()])
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text(lines[0] + "\n" + ",".join(lines[1].split(",")[:-1]) + "\n",
                            encoding="utf-8")
            self.assertEqual(len(audit(path)["malformed_csv_rows"]), 1)


    def test_cli_writes_valid_json_with_real_trailing_newline(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "candidates.csv"
            output = root / "report.json"
            write_csv(source, [row()])
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parents[1] / "audit_issue5_candidate_row_integrity.py"),
                 "--input", str(source), "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = output.read_bytes()
            self.assertTrue(payload.endswith(b"\n"))
            self.assertIsInstance(json.loads(payload), dict)

if __name__ == "__main__":
    unittest.main()

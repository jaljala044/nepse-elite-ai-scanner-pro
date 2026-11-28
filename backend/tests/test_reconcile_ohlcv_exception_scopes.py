import csv
import tempfile
import unittest
from pathlib import Path

from reconcile_ohlcv_exception_scopes import reconcile, write_outputs


class CrossScopeLedgerJoinTests(unittest.TestCase):
    def write(self, root, name, rows):
        path = root / name
        fields = sorted({k for row in rows for k in row})
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_full_outer_join_preserves_overlap_and_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = self.write(root, "left.csv", [
                {"symbol":"HRL","trade_date":"2026-11-19","exception_id":"L1","rule":"invalid_low"},
                {"symbol":"NABIL","trade_date":"2025-01-02","exception_id":"L2","rule":"invalid_high"},
                {"symbol":"NABIL","trade_date":"2025-01-02","exception_id":"L3","rule":"duplicate_date"},
            ])
            right = self.write(root, "right.csv", [
                {"ticker":"HRL","date":"2026-11-19","flag_id":"R1","rule_code":"ohlc_invariant"},
                {"ticker":"API","date":"2025-01-03","flag_id":"R2","rule_code":"invalid_close"},
            ])
            report = reconcile(left, right, left_name="issue4", right_name="smc56")
        self.assertEqual(report["overlap_keys"], 1)
        self.assertEqual(report["left_only_keys"], 1)
        self.assertEqual(report["right_only_keys"], 1)
        hrl = next(x for x in report["joined_records"] if x["symbol"] == "HRL")
        self.assertEqual(hrl["left_records"][0]["exception_id"], "L1")
        self.assertEqual(hrl["right_records"][0]["exception_id"], "R1")
        nabil = next(x for x in report["joined_records"] if x["symbol"] == "NABIL")
        self.assertTrue(nabil["left_duplicate_key"])
        self.assertEqual(nabil["left_rule_multiplicity"], {"duplicate_date":1,"invalid_high":1})
        self.assertEqual(report["left_duplicate_rows_beyond_first"], 1)
        self.assertFalse(report["canonical_promotion_allowed"])

    def test_invalid_keys_are_retained_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = self.write(root, "left.csv", [{"symbol":"BAD","trade_date":"2026-02-30","id":"x"}])
            right = self.write(root, "right.csv", [{"symbol":"NABIL","trade_date":"2026-01-01","id":"y"}])
            report = reconcile(left, right, left_name="a", right_name="b")
        self.assertEqual(report["invalid_key_rows"], 1)
        self.assertEqual(report["invalid_key_records"][0]["raw_record"]["id"], "x")
        self.assertEqual(report["right_only_keys"], 1)

    def test_duplicate_raw_rows_are_counted_without_collapsing_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {"symbol": "API", "trade_date": "2026-01-01", "exception_id": "E1", "rule": "bad_low"}
            left = self.write(root, "left.csv", [row, row])
            right = self.write(root, "right.csv", [{"symbol": "API", "trade_date": "2026-01-01", "id": "R1"}])
            report = reconcile(left, right, left_name="left", right_name="right")
        joined = report["joined_records"][0]
        self.assertEqual(len(joined["left_records"]), 2)
        self.assertEqual(joined["left_exact_duplicate_rows"], 1)
        self.assertEqual(report["left_exact_duplicate_rows"], 1)

    def test_scope_names_must_be_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = self.write(root, "left.csv", [{"symbol": "API", "trade_date": "2026-01-01"}])
            right = self.write(root, "right.csv", [{"symbol": "API", "trade_date": "2026-01-01"}])
            with self.assertRaisesRegex(ValueError, "non-empty and distinct"):
                reconcile(left, right, left_name="same", right_name="same")

    def test_duplicate_csv_headers_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.csv"
            path.write_text("symbol,symbol,trade_date\\nAPI,API,2026-01-01\\n", encoding="utf-8")
            right = self.write(Path(tmp), "right.csv", [{"symbol": "API", "trade_date": "2026-01-01"}])
            with self.assertRaisesRegex(ValueError, "duplicate column"):
                reconcile(path, right, left_name="left", right_name="right")

    def test_ragged_csv_rows_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ragged.csv"
            path.write_text("symbol,trade_date\\nAPI,2026-01-01,EXTRA\\n", encoding="utf-8")
            right = self.write(Path(tmp), "right.csv", [{"symbol": "API", "trade_date": "2026-01-01"}])
            with self.assertRaisesRegex(ValueError, "malformed CSV field count"):
                reconcile(path, right, left_name="left", right_name="right")

    def test_json_and_csv_output_paths_must_not_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "same.out"
            with self.assertRaisesRegex(ValueError, "must be different"):
                write_outputs({"joined_records": []}, path, path)

    def test_exact_source_locators_and_raw_rows_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = self.write(root, "left.csv", [{"symbol":"API","trade_date":"2026-01-01",
                "source_repository":"owner/repo","source_path":"data/API.csv",
                "source_file_sha256":"a"*64,"source_csv_line":"77","raw_ohlc":"1,2,3,4"}])
            right = self.write(root, "right.csv", [{"symbol":"API","trade_date":"2026-01-01",
                "source_repository":"owner/other","source_path":"data/API.csv",
                "source_file_sha256":"b"*64,"source_csv_line":"99","rule":"low_gt_open"}])
            report = reconcile(left, right, left_name="a", right_name="b")
            write_outputs(report, root/"joined.json", root/"joined.csv")
            row = report["joined_records"][0]
            self.assertTrue((root/"joined.json").exists())
            self.assertTrue((root/"joined.csv").exists())
        self.assertEqual(row["left_records"][0]["source_csv_line"], "77")
        self.assertEqual(row["right_records"][0]["source_file_sha256"], "b"*64)


if __name__ == "__main__":
    unittest.main()

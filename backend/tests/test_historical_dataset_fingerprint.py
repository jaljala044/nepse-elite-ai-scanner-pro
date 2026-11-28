import copy
import unittest
from app.historical_dataset_admission import (
    dataset_content_fingerprint, admit_six_scanner_dataset,
)


class DatasetFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"record_id": "NABIL-1", "close": "100",
                      "available_at": "2025-12-30T15:00:00+05:45"},
                     {"record_id": "NABIL-2", "close": "101",
                      "available_at": "2025-12-31T15:00:00+05:45"}]
        self.digest = dataset_content_fingerprint(self.rows)

    def admit(self, rows, digest=None):
        digest = self.digest if digest is None else digest
        return admit_six_scanner_dataset(
            panel_qualification={"status": "PANEL_EVIDENCE_QUALIFIED_FOR_HUMAN_REVIEW",
                "backtest_admission_allowed": False, "dataset_fingerprint": digest},
            dataset_manifest={"dataset_fingerprint": digest,
                "decision_time": "2026-01-01T00:00:00Z",
                "corporate_action_review_status": "verified", "input_lineage_status": "complete"},
            records=rows, expected_dataset_fingerprint=digest,
            decision_time="2026-01-01T00:00:00Z", train_end="2025-01-01T00:00:00Z",
            validation_start="2025-02-01T00:00:00Z", validation_end="2025-12-31T00:00:00Z",
            test_start="2026-02-01T00:00:00Z", test_end="2026-03-01T00:00:00Z")

    def test_unchanged_records_admitted_only_for_review(self):
        result = self.admit(self.rows)
        self.assertEqual(result["status"], "ADMITTED_FOR_HUMAN_REVIEW")
        self.assertEqual(result["computed_dataset_fingerprint"], self.digest)
        self.assertEqual(len(result["matrix"]), 24)
        self.assertFalse(result["replay_started"])
        self.assertFalse(result["production_enabled"])

    def test_tampered_record_blocks_all_24_cells(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["close"] = "999"
        result = self.admit(rows)
        self.assertIn("dataset_content_fingerprint_mismatch", [i["reason"] for i in result["issues"]])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(all(x["status"] == "BLOCKED" for x in result["matrix"]))

    def test_row_order_and_count_bound(self):
        self.assertNotEqual(dataset_content_fingerprint(self.rows[::-1]), self.digest)
        self.assertNotEqual(dataset_content_fingerprint(self.rows[:1]), self.digest)

    def test_object_key_order_invariant(self):
        rows = [dict(reversed(list(row.items()))) for row in self.rows]
        self.assertEqual(dataset_content_fingerprint(rows), self.digest)

    def test_invalid_json_and_empty_dataset_rejected(self):
        for rows in ([], [{"x": float("nan")}], [{"x": float("inf")}], [{1: "x"}], [{"x": (1, 2)}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                dataset_content_fingerprint(rows)

    def test_missing_record_id_blocks_even_matching_fingerprint(self):
        rows = copy.deepcopy(self.rows)
        del rows[0]["record_id"]
        result = self.admit(rows, dataset_content_fingerprint(rows))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("invalid_record_or_timestamp", [i["reason"] for i in result["issues"]])


if __name__ == "__main__":
    unittest.main()

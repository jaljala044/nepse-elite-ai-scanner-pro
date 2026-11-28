import unittest
from unittest.mock import patch
from app import historical_dataset_admission as admission


class QualifiedAdmissionBridgeTests(unittest.TestCase):
    def base(self, **kwargs):
        return {"issues": [], "issue_count": 0, "blocker_count": 0,
                "status": "ADMITTED_FOR_HUMAN_REVIEW",
                "matrix": [{"status": "ADMITTED_FOR_HUMAN_REVIEW"}],
                "canonical_promotion_allowed": False, "production_enabled": False,
                "replay_started": False, "admission_sha256": "old"}

    def call(self, rows):
        with patch.object(admission, "admit_six_scanner_dataset", side_effect=self.base):
            return admission.admit_qualified_six_scanner_dataset(
                panel_qualification={}, dataset_manifest={}, records=rows,
                decision_time="2026-01-01T00:00:00+00:00",
                expected_dataset_fingerprint="x", train_end="2025-01-01T00:00:00+00:00",
                validation_start="2025-02-01T00:00:00+00:00",
                validation_end="2025-03-01T00:00:00+00:00",
                test_start="2026-02-01T00:00:00+00:00",
                test_end="2026-03-01T00:00:00+00:00")

    def test_rejects_row_without_upstream_eligibility(self):
        result = self.call([{"row_status": "eligible_for_review"}])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["replay_started"])

    def test_rejects_quarantined_archive(self):
        result = self.call([{"row_status": "eligible_for_review",
            "historical_segment_eligible": True, "archive_locator_present": True,
            "archive_quarantine_disposition": "excluded_confirmed_carry_forward"}])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["canonical_promotion_allowed"])

    def test_rejects_missing_archive_disposition(self):
        result = self.call([{"row_status": "eligible_for_review",
            "historical_segment_eligible": True, "archive_locator_present": True}])
        self.assertEqual(result["status"], "BLOCKED")

    def test_allows_only_upstream_cleared_review_rows(self):
        result = self.call([{"row_status": "eligible_for_review",
            "historical_segment_eligible": True,
            "archive_quarantine_disposition": "not_in_overlay_requires_other_gates"}])
        self.assertEqual(result["status"], "ADMITTED_FOR_HUMAN_REVIEW")
        self.assertFalse(result["replay_started"])
        self.assertFalse(result["production_enabled"])


if __name__ == "__main__":
    unittest.main()

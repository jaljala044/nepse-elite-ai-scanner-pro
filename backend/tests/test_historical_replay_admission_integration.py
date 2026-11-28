"""End-to-end synthetic admission regression without mocked eligibility."""
import unittest
from app.historical_dataset_admission import (
    admit_qualified_six_scanner_dataset, dataset_content_fingerprint,
)
from test_historical_segment_eligibility import HistoricalSegmentEligibilityTests


class HistoricalReplayAdmissionIntegrationTests(unittest.TestCase):
    def test_exact_evidence_bound_records_reach_review_only(self):
        fixture = HistoricalSegmentEligibilityTests()
        fixture.setUp()
        rows = [dict(row, record_id="NABIL:" + row["session_date"],
                     row_status="eligible_for_review", historical_segment_eligible=True)
                for row in fixture.records]
        digest = dataset_content_fingerprint(rows)
        cutoff = "2026-01-01T00:00:00+05:45"
        args = dict(
            panel_qualification={"status": "PANEL_EVIDENCE_QUALIFIED_FOR_HUMAN_REVIEW",
                                 "backtest_admission_allowed": False,
                                 "dataset_fingerprint": digest},
            dataset_manifest={"dataset_fingerprint": digest, "decision_time": cutoff,
                              "corporate_action_review_status": "verified",
                              "input_lineage_status": "complete"},
            records=rows, decision_time=cutoff, expected_dataset_fingerprint=digest,
            train_end="2025-06-01T00:00:00Z",
            validation_start="2025-07-01T00:00:00Z",
            validation_end="2025-12-31T00:00:00Z",
            test_start="2026-02-01T00:00:00Z", test_end="2026-03-01T00:00:00Z",
            segment_inputs={("NABIL", "123"): {
                "segment": fixture.segment, "expected_sessions": fixture.sessions,
                "session_statuses": fixture.statuses, "session_evidence": fixture.session_evidence,
                "required_sessions": 120, "available_warmup_sessions": 20}})
        result = admit_qualified_six_scanner_dataset(**args)
        self.assertEqual(result["status"], "ADMITTED_FOR_HUMAN_REVIEW", repr(result["issues"]))
        self.assertEqual(len(result["matrix"]), 24)
        self.assertFalse(result["replay_started"])
        self.assertFalse(result["production_enabled"])
        # A changed bar cannot be admitted with the original dataset digest.
        rows[0]["close"] = "999999"
        result = admit_qualified_six_scanner_dataset(**args)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(all(cell["status"] == "BLOCKED" for cell in result["matrix"]))


if __name__ == "__main__":
    unittest.main()

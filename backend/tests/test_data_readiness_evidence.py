import unittest
from app.data_readiness_evidence import assemble_training_evidence


class DataReadinessEvidenceTests(unittest.TestCase):
    def test_missing_all_inputs_blocks_every_gate(self):
        result = assemble_training_evidence(
            universe_report=None, session_reports=None, provenance_reports=None,
            ohlcv_report=None, broker_report=None, point_in_time_report=None)
        self.assertFalse(result["training_readiness"]["training_ready"])
        self.assertTrue(result["training_readiness"]["blockers"])

    def test_complete_explicit_evidence_can_pass(self):
        result = assemble_training_evidence(
            universe_report={"manifest_verified": True},
            session_reports=[{"status": "verified", "session_state": "confirmed_trading_session"}],
            provenance_reports=[{
                "training_eligibility": {"rights_clearance": True},
                "capture": {"payload_sha256": "a" * 64, "source_record_id": "row-1"},
                "provenance_sha256": "b" * 64,
            }],
            ohlcv_report={"integrity_status": "passed", "unresolved_exception_count": 0,
                          "coverage_ratio": 0.99},
            broker_report={"identity_policy_status": "passed",
                            "unresolved_identity_policy_violations": 0,
                            "verified_amount_coverage": 0.97},
            point_in_time_report={"leakage_status": "passed", "future_input_count": 0,
                                  "premature_label_count": 0},
            corporate_action_reviewed=True, holdout_protocol_id="walk-forward-v1",
            historical_coverage=0.99, evidence_snapshot_id="evidence-1")
        self.assertTrue(result["training_readiness"]["training_ready"])

    def test_unknown_rights_do_not_clear(self):
        result = assemble_training_evidence(
            universe_report={"manifest_verified": True},
            session_reports=[{"status": "verified", "session_state": "confirmed_trading_session"}],
            provenance_reports=[{"training_eligibility": {"rights_clearance": False},
                                 "capture": {"payload_sha256": "a" * 64, "source_record_id": "r"}}],
            ohlcv_report={"integrity_status": "passed", "unresolved_exception_count": 0,
                          "coverage_ratio": 0.99},
            broker_report={"identity_policy_status": "passed",
                            "unresolved_identity_policy_violations": 0,
                            "verified_amount_coverage": 0.99},
            point_in_time_report={"leakage_status": "passed", "future_input_count": 0,
                                  "premature_label_count": 0},
            corporate_action_reviewed=True, holdout_protocol_id="wf",
            historical_coverage=0.99)
        self.assertFalse(result["source_rights_cleared"])
        self.assertFalse(result["training_readiness"]["training_ready"])

    def test_missing_session_date_report_blocks_calendar(self):
        result = assemble_training_evidence(
            universe_report={"manifest_verified": True}, session_reports=[],
            provenance_reports=[{"training_eligibility": {"rights_clearance": True},
                                 "capture": {"payload_sha256": "a" * 64, "source_record_id": "r"}}],
            ohlcv_report={"integrity_status": "passed", "unresolved_exception_count": 0,
                          "coverage_ratio": 0.99},
            broker_report={"identity_policy_status": "passed",
                            "unresolved_identity_policy_violations": 0,
                            "verified_amount_coverage": 0.99},
            point_in_time_report={"leakage_status": "passed", "future_input_count": 0,
                                  "premature_label_count": 0},
            corporate_action_reviewed=True, holdout_protocol_id="wf",
            historical_coverage=0.99)
        self.assertFalse(result["session_calendar_verified"])

    def test_malformed_provenance_hash_blocks_lineage(self):
        result = assemble_training_evidence(
            universe_report={"manifest_verified": True},
            session_reports=[{"status": "verified", "session_state": "confirmed_trading_session"}],
            provenance_reports=[{"training_eligibility": {"rights_clearance": True},
                                 "capture": {"payload_sha256": "a" * 64, "source_record_id": "r"},
                                 "provenance_sha256": "not-a-hash"}],
            ohlcv_report={"integrity_status": "passed", "unresolved_exception_count": 0,
                          "coverage_ratio": 0.99},
            broker_report={"identity_policy_status": "passed",
                            "unresolved_identity_policy_violations": 0,
                            "verified_amount_coverage": 0.99},
            point_in_time_report={"leakage_status": "passed", "future_input_count": 0,
                                  "premature_label_count": 0},
            corporate_action_reviewed=True, holdout_protocol_id="wf",
            historical_coverage=0.99)
        self.assertFalse(result["source_lineage_complete"])
        self.assertFalse(result["training_readiness"]["training_ready"])

    def test_missing_source_record_id_blocks_lineage(self):
        result = assemble_training_evidence(
            universe_report={"manifest_verified": True},
            session_reports=[{"status": "verified", "session_state": "confirmed_trading_session"}],
            provenance_reports=[{"training_eligibility": {"rights_clearance": True},
                                 "capture": {"payload_sha256": "a" * 64}}],
            ohlcv_report={"integrity_status": "passed", "unresolved_exception_count": 0,
                          "coverage_ratio": 0.99},
            broker_report={"identity_policy_status": "passed",
                            "unresolved_identity_policy_violations": 0,
                            "verified_amount_coverage": 0.99},
            point_in_time_report={"leakage_status": "passed", "future_input_count": 0,
                                  "premature_label_count": 0},
            corporate_action_reviewed=True, holdout_protocol_id="wf",
            historical_coverage=0.99)
        self.assertFalse(result["source_lineage_complete"])



    def test_non_finite_or_over_one_historical_coverage_blocks(self):
        for coverage in (float("nan"), float("inf"), 1.01, -0.1):
            with self.subTest(coverage=coverage):
                result = assemble_training_evidence(
                    universe_report={"manifest_verified": True},
                    session_reports=[{"status": "verified", "session_state": "confirmed_trading_session"}],
                    provenance_reports=[{"training_eligibility": {"rights_clearance": True},
                                         "capture": {"payload_sha256": "a" * 64, "source_record_id": "r"},
                                         "provenance_sha256": "b" * 64}],
                    ohlcv_report={"integrity_status": "passed", "unresolved_exception_count": 0,
                                  "coverage_ratio": 0.99},
                    broker_report={"identity_policy_status": "passed",
                                    "unresolved_identity_policy_violations": 0,
                                    "verified_amount_coverage": 0.99},
                    point_in_time_report={"leakage_status": "passed", "future_input_count": 0,
                                          "premature_label_count": 0},
                    corporate_action_reviewed=True, holdout_protocol_id="wf",
                    historical_coverage=coverage)
                self.assertFalse(result["historical_coverage_threshold_met"])
                self.assertFalse(result["training_readiness"]["training_ready"])


if __name__ == "__main__":
    unittest.main()

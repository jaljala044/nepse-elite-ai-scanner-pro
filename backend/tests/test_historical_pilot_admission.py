import unittest
from app.historical_pilot_admission import build_pilot_admission_bundle


class PilotAdmissionBundleTests(unittest.TestCase):
    def base(self):
        return dict(
            capture_reports={"C1":{"status":"CAPTURE_VALIDATED","capture_key":"C1","capture_id":"CAPTURE-1"}},
            first_trade_report={"all_cohort_first_trades_verified":True,"verified_count":18,"cohort_count":18,"unresolved_count":0},
            panel_readiness_report={"status":"READY_FOR_BOUNDED_RESEARCH"},
            required_capture_keys=["C1"],
        )

    def test_ready_is_bounded_review_only(self):
        report = build_pilot_admission_bundle(**self.base())
        self.assertEqual(report["status"], "BOUNDED_PILOT_EVIDENCE_READY")
        self.assertTrue(report["bounded_research_review_allowed"])
        self.assertFalse(report["backtest_admission_allowed"])
        self.assertEqual(report["validated_capture_ids"], ["CAPTURE-1"])

    def test_missing_capture_blocks(self):
        args = self.base()
        args["capture_reports"] = {}
        self.assertEqual(build_pilot_admission_bundle(**args)["status"], "BLOCKED")

    def test_unresolved_first_trade_blocks(self):
        args = self.base()
        args["first_trade_report"]["all_cohort_first_trades_verified"] = False
        self.assertEqual(build_pilot_admission_bundle(**args)["status"], "BLOCKED")

    def test_panel_blocked_blocks(self):
        args = self.base()
        args["panel_readiness_report"]["status"] = "BLOCKED"
        self.assertEqual(build_pilot_admission_bundle(**args)["status"], "BLOCKED")

    def test_capture_report_key_mismatch_blocks(self):
        args = self.base()
        args["capture_reports"]["C1"]["capture_key"] = "OTHER"
        self.assertEqual(build_pilot_admission_bundle(**args)["status"], "BLOCKED")

    def test_missing_manifest_capture_id_blocks(self):
        args = self.base()
        args["capture_reports"]["C1"].pop("capture_id")
        self.assertEqual(build_pilot_admission_bundle(**args)["status"], "BLOCKED")

    def test_duplicate_manifest_capture_ids_block(self):
        args = self.base()
        args["required_capture_keys"] = ["C1", "C2"]
        args["capture_reports"]["C2"] = {"status":"CAPTURE_VALIDATED","capture_key":"C2","capture_id":"CAPTURE-1"}
        self.assertEqual(build_pilot_admission_bundle(**args)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()

import unittest
from app.historical_pilot_admission import build_pilot_admission_bundle

class PilotAdmissionBundleTests(unittest.TestCase):
    def base(self):
        return dict(capture_reports={"C1":{"status":"CAPTURE_VALIDATED"}},first_trade_report={"all_cohort_first_trades_verified":True,"verified_count":18,"cohort_count":18,"unresolved_count":0},panel_readiness_report={"status":"READY_FOR_BOUNDED_RESEARCH"},required_capture_ids=["C1"])
    def test_ready_is_bounded_review_only(self):
        r=build_pilot_admission_bundle(**self.base())
        self.assertEqual(r["status"],"BOUNDED_PILOT_EVIDENCE_READY")
        self.assertTrue(r["bounded_research_review_allowed"])
        self.assertFalse(r["backtest_admission_allowed"])
    def test_missing_capture_blocks(self):
        a=self.base(); a["capture_reports"]={}
        r=build_pilot_admission_bundle(**a)
        self.assertEqual(r["status"],"BLOCKED")
    def test_unresolved_first_trade_blocks(self):
        a=self.base(); a["first_trade_report"]["all_cohort_first_trades_verified"]=False
        r=build_pilot_admission_bundle(**a)
        self.assertEqual(r["status"],"BLOCKED")
    def test_panel_blocked_blocks(self):
        a=self.base(); a["panel_readiness_report"]["status"]="BLOCKED"
        r=build_pilot_admission_bundle(**a)
        self.assertEqual(r["status"],"BLOCKED")

if __name__=="__main__": unittest.main()

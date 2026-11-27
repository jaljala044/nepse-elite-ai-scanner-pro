import unittest
from app.historical_pilot_panel import build_lifecycle_panel_readiness

class LifecyclePanelReadinessTests(unittest.TestCase):
    def base(self):
        return dict(cohort_symbols=["AAA"],security_master=[{"symbol":"AAA","security_id":"SEC-1","effective_from":"2025-01-01"}],expected_sessions=[{"session_date":"2025-01-02","status":"confirmed_open","evidence_id":"CAL-1","available_at":"2025-01-02T15:00:00+05:45"}],bars=[{"symbol":"AAA","session_date":"2025-01-02","available_at":"2025-01-02T15:05:00+05:45","raw_sha256":"b"*64,"open":10,"high":12,"low":9,"close":11,"volume":100}],corporate_action_status={"status":"validated_for_research","withheld_events":[],"rejected_events":[]},decision_cutoff="2025-01-03T00:00:00+05:45")
    def test_ready_panel_is_not_promotable(self):
        r=build_lifecycle_panel_readiness(**self.base())
        self.assertEqual(r["status"],"READY_FOR_BOUNDED_RESEARCH")
        self.assertFalse(r["backtest_admission_allowed"])
    def test_missing_bar_blocks(self):
        a=self.base(); a["bars"]=[]
        r=build_lifecycle_panel_readiness(**a)
        self.assertEqual(r["status"],"BLOCKED")
        self.assertEqual(len(r["missing_symbol_sessions"]),1)
    def test_future_bar_blocks(self):
        a=self.base(); a["bars"][0]["available_at"]="2025-01-04T00:00:00+05:45"
        r=build_lifecycle_panel_readiness(**a)
        self.assertEqual(r["bar_errors"][0]["reason"],"bar_after_decision_cutoff")
    def test_unreconciled_actions_block(self):
        a=self.base(); a["corporate_action_status"]={"status":"pending","withheld_events":["CA-1"]}
        r=build_lifecycle_panel_readiness(**a)
        self.assertEqual(r["corporate_actions"],"missing_or_unreconciled")

if __name__=="__main__": unittest.main()

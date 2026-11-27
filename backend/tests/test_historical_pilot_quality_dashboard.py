import unittest
from app.historical_pilot_quality_dashboard import build_historical_pilot_quality_dashboard


class QualityDashboardTests(unittest.TestCase):
    def args(self):
        return dict(
            cohort_symbols=["AAA"],
            security_master=[{"symbol":"AAA","security_id":"S1","effective_from":"2025-01-01"}],
            expected_sessions=[{"session_date":"2025-01-02","status":"confirmed_open","evidence_id":"CAL1"}],
            panel_report={"status":"PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH","panel_rows":[{"symbol":"AAA","session_date":"2025-01-02"}],"conflicts":[],"ingestion_errors":[],"insufficient_source_coverage":[]},
            reconciliation_report={"status":"SOURCE_EVIDENCE_RECONCILED","missing_capture_keys":[],"failed_capture_keys":[],"duplicate_capture_ids":[],"first_trade_report":{"all_cohort_first_trades_verified":True,"verified_count":1,"cohort_count":1,"unresolved_count":0}},
            replay_preflight={"status":"BOUNDED_PILOT_REPLAY_PREFLIGHT_READY","dataset_manifest":{"sha256":"a"*64}},
            corporate_action_status={"status":"validated_for_research","withheld_events":[],"rejected_events":[]},
        )
    def test_clean_dashboard_is_review_only(self):
        out=build_historical_pilot_quality_dashboard(**self.args())
        self.assertEqual(out["status"],"QUALITY_REVIEW_READY")
        self.assertEqual(out["coverage_pct"],100.0)
        self.assertFalse(out["backtest_admission_allowed"])
    def test_missing_bar_blocks_and_is_visible(self):
        args=self.args(); args["panel_report"]["panel_rows"]=[]
        out=build_historical_pilot_quality_dashboard(**args)
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["missing_symbol_sessions"],[{"symbol":"AAA","session_date":"2025-01-02"}])
    def test_corporate_action_exception_blocks(self):
        args=self.args(); args["corporate_action_status"]["withheld_events"]=[{"event":"unresolved"}]
        self.assertEqual(build_historical_pilot_quality_dashboard(**args)["status"],"BLOCKED")


if __name__ == "__main__": unittest.main()

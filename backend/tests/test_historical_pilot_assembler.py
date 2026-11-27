import unittest
from app.historical_pilot_assembler import assemble_lifecycle_pilot_panel

class LifecyclePilotAssemblerTests(unittest.TestCase):
    def row(self, publisher="PUB-1", close=11):
        return {"symbol":"AAA","session_date":"2025-01-02","open":10,"high":12,"low":9,"close":close,"volume":100,"available_at":"2025-01-02T16:00:00+05:45","source_id":"SRC-"+publisher,"publisher_id":publisher,"raw_sha256":"a"*64,"capture_id":"CAP-"+publisher,"page_number":1,"source_row_number":2,"row_sha256":("b" if close==11 else "c")*64}
    def base(self, reports=None, sessions=None):
        return dict(cohort_symbols=["AAA"],security_master=[{"symbol":"AAA","security_id":"SEC-1","effective_from":"2025-01-01"}],expected_sessions=sessions if sessions is not None else [{"session_date":"2025-01-02","status":"confirmed_open","evidence_id":"CAL-1","available_at":"2025-01-02T15:00:00+05:45"}],ingestion_reports=reports if reports is not None else [{"status":"INGESTED","all_rows_accepted":True,"rows":[self.row()]}],corporate_action_status={"status":"validated_for_research","withheld_events":[],"rejected_events":[]},decision_cutoff="2025-01-03T00:00:00+05:45")
    def test_assembles_bounded_panel(self):
        r=assemble_lifecycle_pilot_panel(**self.base())
        self.assertEqual(r["status"],"PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH")
        self.assertEqual(r["panel_row_count"],1)
        self.assertFalse(r["backtest_admission_allowed"])
    def test_cross_source_conflict_quarantined(self):
        reports=[{"status":"INGESTED","all_rows_accepted":True,"rows":[self.row()]},{"status":"INGESTED","all_rows_accepted":True,"rows":[self.row("PUB-2",12)]}]
        r=assemble_lifecycle_pilot_panel(**self.base(reports=reports))
        self.assertEqual(r["status"],"BLOCKED")
        self.assertEqual(r["conflicts"][0]["reason"],"cross_source_ohlcv_conflict")
    def test_missing_expected_session_bar_blocks(self):
        a=self.base(); a["ingestion_reports"]=[{"status":"INGESTED","all_rows_accepted":True,"rows":[]}]
        r=assemble_lifecycle_pilot_panel(**a)
        self.assertEqual(r["status"],"BLOCKED")
        self.assertEqual(len(r["readiness_report"]["missing_symbol_sessions"]),1)
    def test_independent_publisher_threshold_blocks(self):
        r=assemble_lifecycle_pilot_panel(**self.base(),minimum_independent_sources=2)
        self.assertEqual(r["status"],"BLOCKED")
        self.assertEqual(r["insufficient_source_coverage"][0]["required_independent_publishers"],2)

if __name__=="__main__": unittest.main()

import unittest
from app.historical_pilot_panel_qualification import qualify_historical_evidence_panel

def report(rows):
    return {"status":"INGESTED","all_rows_accepted":True,"rows":rows}

class HistoricalPanelQualificationTests(unittest.TestCase):
    def test_complete_bounded_cohort_qualifies_only_for_human_review(self):
        evidence={
            "official_market_calendar":report([{"session_date":"2025-01-02","is_open":True}]),
            "official_security_master":report([{"symbol":"AAA","security_id":"SEC-1","effective_from":"2024-01-01","effective_to":None}]),
            "official_corporate_actions":report([{"symbol":"AAA","action_id":"ACT-1"}]),
            "cdsc_first_trade":report([{"symbol":"AAA","first_trade_date":"2025-01-02"}])}
        att={"complete_for_requested_window":True,"human_reviewed":True,"reviewer_id":"reviewer","evidence_reference":"official-review-1","window_start":"2025-01-02","window_end":"2025-01-02"}
        out=qualify_historical_evidence_panel(cohort_symbols=["AAA"],expected_sessions=["2025-01-02"],ohlcv_ingestion_reports=[report([{"symbol":"AAA","session_date":"2025-01-02"}])],evidence_ingestion_reports=evidence,corporate_action_coverage_attestation=att,decision_cutoff="2025-01-03T00:00:00+05:45",dataset_fingerprint="f"*64)
        self.assertEqual(out["status"],"PANEL_EVIDENCE_QUALIFIED_FOR_HUMAN_REVIEW",msg=repr(out["errors"]))
        self.assertFalse(out["backtest_admission_allowed"])
        self.assertEqual(out["dataset_fingerprint"],"f"*64)

    def test_expected_session_after_nepal_local_cutoff_blocks_panel(self):
        out=qualify_historical_evidence_panel(
            cohort_symbols=["AAA"],expected_sessions=["2025-01-02","2025-01-03"],
            ohlcv_ingestion_reports=[],evidence_ingestion_reports={},
            corporate_action_coverage_attestation={},
            decision_cutoff="2025-01-02T18:00:00+00:00")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["errors"][0]["reason"],"expected_session_after_decision_cutoff")
        self.assertEqual(out["errors"][0]["sessions"],["2025-01-03"])

    def test_decision_cutoff_requires_timezone_aware_canonical_timestamp(self):
        for cutoff in ("2025-01-03T00:00:00", "20250103T00:00:00+05:45", "2025-01-03"):
            with self.subTest(cutoff=cutoff):
                out=qualify_historical_evidence_panel(
                    cohort_symbols=["AAA"],expected_sessions=["2025-01-02"],
                    ohlcv_ingestion_reports=[],evidence_ingestion_reports={},
                    corporate_action_coverage_attestation={},decision_cutoff=cutoff)
                self.assertEqual(out["status"],"BLOCKED")
                self.assertEqual(out["errors"][0]["reason"],"cohort_or_session_window_invalid")

    def test_nepal_local_cutoff_accepts_same_utc_day_if_local_session_date_has_arrived(self):
        out=qualify_historical_evidence_panel(
            cohort_symbols=["AAA"],expected_sessions=["2025-01-03"],
            ohlcv_ingestion_reports=[],evidence_ingestion_reports={},
            corporate_action_coverage_attestation={},
            decision_cutoff="2025-01-02T23:00:00+00:00")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertNotEqual(out["errors"][0]["reason"],"expected_session_after_decision_cutoff")

    def test_missing_calendar_and_action_attestation_block_qualification(self):
        out=qualify_historical_evidence_panel(cohort_symbols=["AAA"],expected_sessions=["2025-01-02"],ohlcv_ingestion_reports=[report([{"symbol":"AAA","session_date":"2025-01-02"}])],evidence_ingestion_reports={},corporate_action_coverage_attestation={},decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertFalse(out["production_enabled"])

if __name__=="__main__":unittest.main()

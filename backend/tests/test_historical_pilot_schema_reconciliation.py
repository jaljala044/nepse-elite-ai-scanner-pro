import unittest
from app.historical_pilot_schema_profiles import validate_source_schema_profile
from app.historical_pilot_cross_dataset_reconciliation import reconcile_historical_datasets

class SchemaProfileTests(unittest.TestCase):
    def test_explicit_approved_versioned_profile_passes(self):
        p={"profile_id":"nepse-calendar-v1","version":"1.0.0","source_id":"src-1","publisher_id":"pub-1",
           "dataset_kind":"official_market_calendar","column_map":{"session_date":"Date","is_open":"Open","session_type":"Type"},
           "approved_by":"reviewer","approval_reference":"review-123","approved_at":"2026-01-01T00:00:00+05:45","approved":True}
        out=validate_source_schema_profile(p)
        self.assertEqual(out["status"],"APPROVED_PROFILE_VALID")
        self.assertEqual(len(out["profile_sha256"]),64)
    def test_unapproved_or_missing_schema_fields_block(self):
        out=validate_source_schema_profile({"dataset_kind":"official_market_calendar","column_map":{},"approved":False})
        self.assertEqual(out["status"],"BLOCKED")
        self.assertIsNone(out["column_map"])

class CrossDatasetReconciliationTests(unittest.TestCase):
    def fixture(self):
        def rep(rows): return {"status":"INGESTED","all_rows_accepted":True,"rows":rows}
        evidence={"official_market_calendar":rep([{"session_date":"2025-01-02","is_open":True}]),
          "official_security_master":rep([{"symbol":"AAA","effective_from":"2024-01-01","effective_to":None}]),
          "official_corporate_actions":rep([{"symbol":"AAA","ex_date":"2025-01-02"}]),
          "cdsc_first_trade":rep([{"symbol":"AAA","first_trade_date":"2025-01-02"}]),
          "official_floorsheet":rep([{"symbol":"AAA","session_date":"2025-01-02"}]),
          "official_sector_indices":rep([{"sector":"BANK","session_date":"2025-01-02"}]),
          "official_broker_trade_summary":rep([{"symbol":"AAA","session_date":"2025-01-02"}])}
        return evidence,rep
    def test_consistent_panel_stays_human_review_only(self):
        evidence,rep=self.fixture()
        out=reconcile_historical_datasets(cohort_symbols=["AAA"],expected_sessions=["2025-01-02"],
          ohlcv_ingestion_reports=[rep([{"symbol":"AAA","session_date":"2025-01-02"}])],evidence_ingestion_reports=evidence)
        self.assertEqual(out["status"],"CONSISTENT_FOR_HUMAN_REVIEW")
        self.assertFalse(out["backtest_admission_allowed"])
    def test_calendar_and_first_trade_conflicts_are_blockers(self):
        evidence,rep=self.fixture()
        evidence["official_market_calendar"]["rows"][0]["is_open"]=False
        evidence["cdsc_first_trade"]["rows"][0]["first_trade_date"]="2024-12-01"
        out=reconcile_historical_datasets(cohort_symbols=["AAA"],expected_sessions=["2025-01-02"],
          ohlcv_ingestion_reports=[rep([{"symbol":"AAA","session_date":"2025-01-02"}])],evidence_ingestion_reports=evidence)
        self.assertGreaterEqual(out["blocker_count"],2)
        self.assertEqual(out["status"],"REVIEW_REQUIRED")

if __name__=="__main__": unittest.main()

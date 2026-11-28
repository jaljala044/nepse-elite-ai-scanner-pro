import unittest
from app.historical_pilot_panel_pipeline import build_historical_pilot_panel_review


class PanelPipelineTests(unittest.TestCase):
    def test_unreconciled_sources_block_panel_pipeline_before_assembly(self):
        out=build_historical_pilot_panel_review(cohort_symbols=["AAA"],security_master=[],expected_sessions=[],ohlcv_ingestion_reports=[],corporate_action_status={},source_reconciliation_report={"status":"BLOCKED"},decision_cutoff="2025-02-02T00:00:00+05:45",required_capture_keys=["EOD"])
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["reason"],"source_reconciliation_not_passed")
        self.assertFalse(out["backtest_admission_allowed"])
    def test_unaccepted_ohlcv_report_blocks_panel_pipeline(self):
        out=build_historical_pilot_panel_review(cohort_symbols=["AAA"],security_master=[],expected_sessions=[],ohlcv_ingestion_reports=[{"status":"BLOCKED","all_rows_accepted":False}],corporate_action_status={},source_reconciliation_report={"status":"SOURCE_EVIDENCE_RECONCILED"},decision_cutoff="2025-02-02T00:00:00+05:45",required_capture_keys=["EOD"])
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["reason"],"one_or_more_ohlcv_ingestion_reports_not_fully_accepted")


if __name__=="__main__":unittest.main()

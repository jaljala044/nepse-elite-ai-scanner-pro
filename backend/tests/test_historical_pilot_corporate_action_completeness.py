import unittest
from app.historical_pilot_corporate_action_verification import verify_corporate_actions
from app.historical_pilot_completeness_audit import audit_historical_panel_completeness

class CorporateActionVerificationTests(unittest.TestCase):
    def rows(self,kind="bonus",n=1,d=1,cash=None,rights=None):
        base={"symbol":"AAA","action_type":kind,"ex_date":"2025-01-03","terms_reference":"TERM-1","ratio_numerator":n,"ratio_denominator":d,"cash_amount":cash,"rights_issue_price":rights}
        return ({**base,"source_id":"SRC-A","publisher_id":"PUB-A"},{**base,"source_id":"SRC-B","publisher_id":"PUB-B"})
    def test_bonus_factor_requires_two_publishers_and_approved_method(self):
        a,b=self.rows()
        out=verify_corporate_actions(primary_rows=[a],secondary_rows=[b],previous_closes={"AAA":100},approved_conventions={"bonus":"THEORETICAL_EX_PRICE_V1"})
        self.assertEqual(out["status"],"VERIFIED"); self.assertAlmostEqual(out["events"][0]["adjustment_factor"],0.5); self.assertFalse(out["automatic_adjustment_applied"])
    def test_conflicting_terms_and_single_source_are_not_verified(self):
        a,b=self.rows(); b["ratio_numerator"]=2
        out=verify_corporate_actions(primary_rows=[a],secondary_rows=[b],previous_closes={"AAA":100},approved_conventions={"bonus":"THEORETICAL_EX_PRICE_V1"})
        self.assertEqual(out["verified_event_count"],0)
        out=verify_corporate_actions(primary_rows=[a],secondary_rows=[],previous_closes={"AAA":100},approved_conventions={"bonus":"THEORETICAL_EX_PRICE_V1"})
        self.assertEqual(out["errors"][0]["reason"],"two_independent_sources_required")
    def test_cash_dividend_and_rights_factors(self):
        a,b=self.rows("cash_dividend",cash=10)
        out=verify_corporate_actions(primary_rows=[a],secondary_rows=[b],previous_closes={"AAA":100},approved_conventions={"cash_dividend":"THEORETICAL_EX_PRICE_V1"})
        self.assertAlmostEqual(out["events"][0]["adjustment_factor"],0.9)
        a,b=self.rows("rights",n=1,d=2,rights=50)
        out=verify_corporate_actions(primary_rows=[a],secondary_rows=[b],previous_closes={"AAA":100},approved_conventions={"rights":"THEORETICAL_EX_PRICE_V1"})
        self.assertAlmostEqual(out["events"][0]["adjustment_factor"],250/300)

class CompletenessAuditTests(unittest.TestCase):
    def report(self,rows): return {"status":"INGESTED","all_rows_accepted":True,"rows":rows}
    def test_full_bounded_open_session_coverage(self):
        out=audit_historical_panel_completeness(cohort_symbols=["AAA"],expected_sessions=["2025-01-02","2025-01-03"],ohlcv_ingestion_reports=[self.report([{"symbol":"AAA","session_date":"2025-01-02"},{"symbol":"AAA","session_date":"2025-01-03"}])],official_calendar_report=self.report([{"session_date":"2025-01-02","is_open":True},{"session_date":"2025-01-03","is_open":True}]),security_master_report=self.report([{"symbol":"AAA","effective_from":"2024-01-01","effective_to":None}]),first_trade_report=self.report([{"symbol":"AAA","first_trade_date":"2024-01-01"}]))
        self.assertEqual(out["status"],"COMPLETE_FOR_HUMAN_REVIEW"); self.assertEqual(out["overall_coverage_ratio"],1.0); self.assertFalse(out["backtest_admission_allowed"])
    def test_missing_open_bar_is_blocker_closed_session_is_excluded(self):
        out=audit_historical_panel_completeness(cohort_symbols=["AAA"],expected_sessions=["2025-01-02","2025-01-03"],ohlcv_ingestion_reports=[self.report([{"symbol":"AAA","session_date":"2025-01-02"}])],official_calendar_report=self.report([{"session_date":"2025-01-02","is_open":True},{"session_date":"2025-01-03","is_open":False}]),security_master_report=self.report([{"symbol":"AAA","effective_from":"2024-01-01","effective_to":None}]),first_trade_report=self.report([{"symbol":"AAA","first_trade_date":"2024-01-01"}]))
        self.assertEqual(out["status"],"INCOMPLETE_OR_CONFLICTED"); self.assertEqual(out["symbol_coverage"]["AAA"]["eligible_open_sessions"],1); self.assertGreater(out["blocker_count"],0)

if __name__=="__main__": unittest.main()

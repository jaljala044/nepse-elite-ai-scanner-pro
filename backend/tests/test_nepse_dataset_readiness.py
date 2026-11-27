import unittest
from app.nepse_dataset_readiness import assess_historical_dataset_readiness
from app.nepse_corporate_action_reconciliation import reconcile_corporate_actions, apply_reconciled_adjustments

def report(kind, rows, source="SRC1", publisher="Publisher A"):
    return {"dataset_kind":kind,"status":"validated_for_research",
        "source_envelope":{"source_id":source,"publisher":publisher,"available_at":"2026-01-01T00:00:00+00:00"},
        "validation":{"accepted_rows":rows}}

class DatasetReadinessTests(unittest.TestCase):
    def data(self):
        return {
          "session_calendar":report("session_calendar",[
            {"session_date":"2026-01-02","session_status":"OPEN"},{"session_date":"2026-01-03","session_status":"OPEN"}]),
          "instrument_universe":report("instrument_universe",[
            {"security_id":"SID1","symbol":"AAA","effective_from":"2025-01-01","listing_status":"ACTIVE"}]),
          "ohlcv":report("ohlcv",[
            {"security_id":"SID1","session_date":"2026-01-02","open":"10","high":"11","low":"9","close":"10","volume":"100","turnover":"1000"},
            {"security_id":"SID1","session_date":"2026-01-03","open":"10","high":"12","low":"9","close":"11","volume":"120","turnover":"1300"}]),
          "corporate_actions":report("corporate_actions",[
            {"security_id":"SID1","action_type":"dividend","announcement_date":"2025-12-01","effective_date":"2026-01-02","status":"approved"}])}
    def assess(self,data):
        return assess_historical_dataset_readiness(intake_reports=data,start_date="2026-01-02",
            end_date="2026-01-03",decision_cutoff="2026-01-04T00:00:00+00:00")
    def test_required_core_passes_with_optional_gaps_as_partial(self):
        out=self.assess(self.data())
        self.assertEqual(out["status"],"PARTIAL")
        self.assertEqual(out["ohlcv_session_coverage_pct"],"100")
        self.assertTrue(out["research_panel_assembly_allowed"])
        self.assertEqual(out["inventory"]["floorsheet"]["availability"],"missing_optional")
    def test_missing_bar_blocks_with_symbol_gap(self):
        data=self.data();data["ohlcv"]["validation"]["accepted_rows"].pop()
        out=self.assess(data)
        self.assertEqual(out["status"],"BLOCKED")
        self.assertIn("2026-01-03",out["per_security_coverage"][0]["missing_sessions"])
    def test_duplicate_bar_blocks(self):
        data=self.data();data["ohlcv"]["validation"]["accepted_rows"].append(dict(data["ohlcv"]["validation"]["accepted_rows"][0]))
        out=self.assess(data)
        self.assertTrue(out["duplicate_ohlcv_records"])
        self.assertEqual(out["status"],"BLOCKED")
    def test_future_report_rejected(self):
        data=self.data();data["ohlcv"]["source_envelope"]["available_at"]="2026-01-05T00:00:00+00:00"
        out=self.assess(data)
        self.assertEqual(out["status"],"BLOCKED")
        self.assertIn("not_point_in_time:ohlcv",out["errors"])
    def test_required_optional_dataset_can_be_promoted_to_gate(self):
        out=assess_historical_dataset_readiness(intake_reports=self.data(),start_date="2026-01-02",
            end_date="2026-01-03",decision_cutoff="2026-01-04T00:00:00+00:00",require_optional=("floorsheet",))
        self.assertEqual(out["status"],"BLOCKED")

class CorporateActionTests(unittest.TestCase):
    def records(self, factor="0.9"):
        base={"security_id":"SID1","action_type":"bonus","announcement_date":"2025-12-01",
            "effective_date":"2026-01-02","status":"approved","price_adjustment_factor":factor,
            "volume_adjustment_factor":"1.111111","available_at":"2026-01-01T00:00:00+00:00",
            "rights_status":"approved","source_validation_status":"verified","finality_status":"final",
            "publisher":"Publisher A","evidence_id":"E1","raw_sha256":"a"*64}
        second=dict(base,source_id="SRC2",publisher="Publisher B",evidence_id="E2")
        first=dict(base,source_id="SRC1")
        return [first,second]
    def test_two_sources_with_matching_factors_reconcile(self):
        out=reconcile_corporate_actions(action_records=self.records(),decision_cutoff="2026-01-04T00:00:00+00:00")
        self.assertEqual(out["status"],"validated_for_research")
        self.assertEqual(len(out["reconciled_events"]),1)
    def test_factor_conflict_is_withheld(self):
        rows=self.records();rows[1]["price_adjustment_factor"]="0.8"
        out=reconcile_corporate_actions(action_records=rows,decision_cutoff="2026-01-04T00:00:00+00:00")
        self.assertEqual(out["status"],"blocked_or_partial")
        self.assertEqual(out["withheld_events"][0]["reason"],"source_terms_or_adjustment_factors_disagree")
    def test_one_source_is_not_enough(self):
        out=reconcile_corporate_actions(action_records=self.records()[:1],decision_cutoff="2026-01-04T00:00:00+00:00")
        self.assertEqual(out["withheld_events"][0]["reason"],"two_independent_publishers_required")
    def test_adjustment_applies_only_pre_effective_bars(self):
        event=reconcile_corporate_actions(action_records=self.records(),decision_cutoff="2026-01-04T00:00:00+00:00")["reconciled_events"]
        bars=[{"security_id":"SID1","session_date":"2026-01-01","open":"10","high":"11","low":"9","close":"10","volume":"100","turnover":"1000"},
              {"security_id":"SID1","session_date":"2026-01-02","open":"11","high":"12","low":"10","close":"11","volume":"100","turnover":"1100"}]
        out=apply_reconciled_adjustments(bars=bars,reconciled_events=event,decision_cutoff="2026-01-04T00:00:00+00:00")
        self.assertEqual(out["adjusted_bar_count"],1)
        self.assertEqual(out["bars"][0]["close"],"9.0")
        self.assertEqual(out["bars"][1]["close"],"11")
        self.assertEqual(out["bars"][0]["turnover"],"1000")

if __name__=="__main__": unittest.main()

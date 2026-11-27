import unittest
from app.nepse_historical_panel import assemble_historical_panel
from app.nepse_walk_forward import build_walk_forward_folds

def report(rows, kind, source="SRC"):
    return {"status":"validated_for_research","research_review_allowed":True,
        "available_at":"2025-01-01T12:00:00+05:45","source_id":source,
        "evidence_id":"EV-"+kind,"accepted_rows":rows}

def datasets():
    cal=[{"session_date":d,"session_status":"OPEN"} for d in ("2025-01-01","2025-01-02","2025-01-03")]
    universe=[{"security_id":"S1","symbol":"AAA","effective_from":"2024-01-01","listing_status":"ACTIVE"}]
    bars=[{"security_id":"S1","session_date":d,"open":"100","high":"105","low":"95","close":"102","volume":"1000","turnover":"102000"} for d in ("2025-01-01","2025-01-02","2025-01-03")]
    actions=[{"security_id":"S1","action_type":"dividend","announcement_date":"2024-12-01","effective_date":"2024-12-15","status":"completed"}]
    return {"ohlcv":report(bars,"ohlcv"),"session_calendar":report(cal,"calendar"),
        "instrument_universe":report(universe,"universe"),"corporate_actions":report(actions,"actions")}

class PanelTests(unittest.TestCase):
    def test_complete_common_panel_admitted_without_in_sample_actions(self):
        ds=datasets()
        # Dividend effective before sample; no adjustment event occurs inside sample.
        out=assemble_historical_panel(datasets=ds,start_date="2025-01-01",end_date="2025-01-03",decision_cutoff="2025-01-04T12:00:00+05:45")
        self.assertEqual(out["status"],"validated_for_research")
        self.assertEqual(out["eligible_symbols"],["AAA"])
        self.assertEqual(out["panel_rows"],3)
    def test_missing_session_excludes_symbol(self):
        ds=datasets(); ds["ohlcv"]["accepted_rows"].pop()
        out=assemble_historical_panel(datasets=ds,start_date="2025-01-01",end_date="2025-01-03",decision_cutoff="2025-01-04T12:00:00+05:45")
        self.assertNotIn("AAA",out["eligible_symbols"])
        self.assertTrue(any("incomplete_session_history" in x for x in out["excluded_symbols"]["AAA"]))
    def test_unresolved_split_action_excludes_symbol(self):
        ds=datasets(); ds["corporate_actions"]["accepted_rows"].append({"security_id":"S1","action_type":"split","effective_date":"2025-01-02","status":"completed"})
        out=assemble_historical_panel(datasets=ds,start_date="2025-01-01",end_date="2025-01-03",decision_cutoff="2025-01-04T12:00:00+05:45")
        self.assertNotIn("AAA",out["eligible_symbols"])
    def test_dataset_available_after_cutoff_blocks_entire_panel(self):
        ds=datasets(); ds["ohlcv"]["available_at"]="2025-01-05T12:00:00+05:45"
        out=assemble_historical_panel(datasets=ds,start_date="2025-01-01",end_date="2025-01-03",decision_cutoff="2025-01-04T12:00:00+05:45")
        self.assertEqual(out["status"],"blocked")
    def test_universe_missing_excludes_symbol(self):
        ds=datasets(); ds["instrument_universe"]["accepted_rows"]=[]
        out=assemble_historical_panel(datasets=ds,start_date="2025-01-01",end_date="2025-01-03",decision_cutoff="2025-01-04T12:00:00+05:45")
        self.assertEqual(out["status"],"blocked")

class WalkForwardTests(unittest.TestCase):
    def dates(self,n):
        from datetime import date,timedelta
        start=date(2020,1,1)
        return [(start+timedelta(days=i)).isoformat() for i in range(n)]
    def test_expanding_folds_are_forward_and_embargoed(self):
        out=build_walk_forward_folds(session_dates=self.dates(1000),minimum_train_sessions=300,
            validation_sessions=60,out_of_sample_sessions=60,step_sessions=60,embargo_sessions=120,maximum_folds=3)
        self.assertEqual(out["fold_count"],3)
        for f in out["folds"]:
            self.assertEqual(f["validation"]["start_index"]-f["train"]["end_index"],120)
            self.assertEqual(f["out_of_sample"]["start_index"]-f["validation"]["end_index"],120)
            self.assertLess(f["train"]["end_index"],f["validation"]["start_index"])
            self.assertLess(f["validation"]["end_index"],f["out_of_sample"]["start_index"])
    def test_insufficient_history_returns_no_folds(self):
        out=build_walk_forward_folds(session_dates=self.dates(100),minimum_train_sessions=80,
            validation_sessions=30,out_of_sample_sessions=30,embargo_sessions=20)
        self.assertEqual(out["status"],"insufficient_history")
    def test_unsorted_or_duplicate_dates_rejected(self):
        with self.assertRaisesRegex(ValueError,"unique_and_chronological"):
            build_walk_forward_folds(session_dates=["2025-01-02","2025-01-01"]*10)
    def test_embargo_must_be_nonnegative(self):
        with self.assertRaisesRegex(ValueError,"non_negative"):
            build_walk_forward_folds(session_dates=self.dates(100),embargo_sessions=-1)

if __name__=="__main__": unittest.main()

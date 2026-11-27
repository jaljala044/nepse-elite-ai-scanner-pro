import unittest
from app.idpat_price_volume_engine import idpat_price_volume_features
from app.historical_signal_generation import generate_historical_research_signals

class WyckoffSequenceTests(unittest.TestCase):
    def test_insufficient_and_duplicate_history_withheld(self):
        self.assertEqual(idpat_price_volume_features([])["status"],"insufficient_evidence")
        rows=[{"session_date":"2025-01-01","open":1,"high":2,"low":.5,"close":1,"volume":10} for _ in range(5)]
        self.assertEqual(idpat_price_volume_features(rows)["reason"],"missing_or_duplicate_session_dates")
    def test_sos_candidate_is_descriptive_and_unscored(self):
        rows=[]
        vals=[(10,10.2,9.8,10,100),(10,10.2,9.8,10,100),(10,10.2,9.8,10,100),(10,10.2,9.8,10,100),(10,10.2,9.8,10,100),(10,12,10,11.8,300)]
        for i,(o,h,l,c,v) in enumerate(vals):
            rows.append({"session_date":f"2025-01-{i+1:02d}","open":o,"high":h,"low":l,"close":c,"volume":v})
        out=idpat_price_volume_features(rows,lookback=5)
        self.assertIsNone(out["score"])
        self.assertTrue(any(e["event"]=="SOS_candidate" for e in out["events"]))
        self.assertTrue(any(e["event"]=="Jump_Across_Creek_candidate" for e in out["events"]))

class HistoricalSignalTests(unittest.TestCase):
    def test_missing_trade_context_never_generates_buy(self):
        series={"snapshots":[{"decision_time":"2026-11-27T12:00:00+05:45","as_of_session":"2026-11-27","feature_series":{"AAA":{"trend_momentum":{"qualification_by_horizon":{"swing":{"status":"research_ranked","score":"90","evidence_coverage_pct":"100"}}}}}}]}
        out=generate_historical_research_signals(feature_series=series,signal_contexts={})
        self.assertEqual(out["research_buy_count"],0)
        self.assertEqual(out["withheld"][0]["reason"],"trade_context_missing")
    def test_unverified_gates_and_no_plan_force_no_trade(self):
        series={"snapshots":[{"decision_time":"2026-11-27T12:00:00+05:45","as_of_session":"2026-11-27","feature_series":{"AAA":{"trend_momentum":{"qualification_by_horizon":{"swing":{"status":"research_ranked","score":"90","evidence_coverage_pct":"100","accepted_evidence_clusters":{}}}}}}}]}
        key="2026-11-27T06:15:00+00:00|AAA|trend_momentum|swing"
        out=generate_historical_research_signals(feature_series=series,signal_contexts={key:{"gates":{},"levels":{},"round_trip_cost_pct":"0.4","slippage_pct":"0.2","execution_snapshot":None}})
        self.assertEqual(out["research_buy_count"],0)
        self.assertEqual(out["signals"][0]["action"],"NO_TRADE")
        self.assertIn("trade_plan_unavailable",out["signals"][0]["qualification_failures"])

if __name__=="__main__":unittest.main()

import unittest
from app.idpat_price_volume_engine import idpat_price_volume_features
from app.scanner_decision_pipeline import build_research_decision

class IdpatEngineTests(unittest.TestCase):
    def test_insufficient_history_fails_closed(self):
        out=idpat_price_volume_features([])
        self.assertEqual(out["status"],"insufficient_evidence")
        self.assertIsNone(out["score"])
    def test_detects_spring_candidate_without_claiming_confirmed_spring(self):
        rows=[]
        closes=[10,10.2,10.1,10.3,10.2,10.0,10.4]
        for i,c in enumerate(closes):
            low=9.5 if i==5 else c-.1
            high=c+.2
            rows.append({"session_date":f"2025-01-{i+1:02d}","open":c,"high":high,"low":low,"close":c,"volume":1000})
        out=idpat_price_volume_features(rows,lookback=5)
        self.assertEqual(out["status"],"observed_descriptive_only")
        self.assertTrue(any(e["event"]=="spring_candidate" for e in out["events"]))
        self.assertIsNone(out["score"])
    def test_duplicate_sessions_rejected(self):
        rows=[{"session_date":"2025-01-01","open":1,"high":2,"low":.5,"close":1,"volume":10} for _ in range(5)]
        self.assertEqual(idpat_price_volume_features(rows)["reason"],"missing_or_duplicate_session_dates")

class DecisionPipelineTests(unittest.TestCase):
    def test_missing_execution_snapshot_forces_no_trade(self):
        out=build_research_decision(symbol="ABC",horizon="swing",
            decision_time="2026-11-27T12:00:00+05:45",component_evidence={},
            gate_evidence={},levels={},round_trip_cost_pct=0,slippage_pct=0,
            execution_snapshot=None)
        self.assertEqual(out["action"],"NO_TRADE")
        self.assertEqual(out["execution_check"]["status"],"blocked")
        self.assertFalse(out["production_enabled"])
    def test_unverified_levels_force_no_trade(self):
        out=build_research_decision(symbol="ABC",horizon="swing",
            decision_time="2026-11-27T12:00:00+05:45",component_evidence={},
            gate_evidence={},levels={"entry":{"low":10,"high":11}},
            round_trip_cost_pct=0,slippage_pct=0,
            execution_snapshot={"quote_available":True,"quote_age_seconds":1,
                "max_quote_age_seconds":5,"circuit_state":"normal","spread_pct":.1,
                "max_spread_pct":1,"bid_depth_value":1000})
        self.assertEqual(out["action"],"NO_TRADE")
        self.assertEqual(out["trade_plan"]["status"],"withheld")

if __name__=="__main__":unittest.main()

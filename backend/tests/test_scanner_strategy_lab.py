import unittest
from app.scanner_strategy_lab import HORIZONS, STRATEGIES, evaluate_strategy, settlement_aware_exit_status, strategy_catalog
CUTOFF="2026-11-27T12:00:00+05:45"
def evidence_for(sid):
 return {f:{"score":80,"status":"verified","source_id":"SRC-"+f,"evidence_id":"EV-"+f,"available_at":"2026-11-27T11:00:00+05:45"} for f in STRATEGIES[sid]["weights"]}
class StrategyLabTests(unittest.TestCase):
 def test_six_engines_four_horizons_and_weights(self):
  c=strategy_catalog(); self.assertEqual(len(c["strategies"]),6); self.assertEqual(set(c["horizons_minimum_sessions"]),set(HORIZONS)); self.assertTrue(all(x["weight_total"]==100 for x in c["strategies"].values()))
 def test_all_engines_run_on_each_horizon(self):
  for sid in STRATEGIES:
   for horizon,minimum in HORIZONS.items():
    r=evaluate_strategy(strategy_id=sid,symbol="TEST",horizon=horizon,decision_time=CUTOFF,history_sessions=minimum,feature_evidence=evidence_for(sid))
    self.assertEqual(r["status"],"research_ranked"); self.assertIsNone(r["probability"])
 def test_missing_evidence_not_neutral(self):
  d=evidence_for("trend_momentum"); del d["liquidity"]
  r=evaluate_strategy(strategy_id="trend_momentum",symbol="TEST",horizon="t_plus_2",decision_time=CUTOFF,history_sessions=21,feature_evidence=d)
  self.assertEqual(r["status"],"withheld"); self.assertIn("liquidity",r["missing_features"])
 def test_future_evidence_rejected(self):
  d=evidence_for("trend_momentum"); d["trend"]["available_at"]="2026-11-27T13:00:00+05:45"
  r=evaluate_strategy(strategy_id="trend_momentum",symbol="TEST",horizon="swing",decision_time=CUTOFF,history_sessions=40,feature_evidence=d)
  self.assertEqual(r["status"],"withheld"); self.assertIn("trend",r["rejected_features"])
 def test_hybrid_deduplicates_correlated_structure(self):
  r=evaluate_strategy(strategy_id="hybrid_consensus",symbol="TEST",horizon="swing",decision_time=CUTOFF,history_sessions=40,feature_evidence=evidence_for("hybrid_consensus"))
  c=r["accepted_evidence_clusters"]["price_structure"]; self.assertEqual(c["credited_weight"],"15"); self.assertEqual(set(c["cluster_members_observed"]),{"wyckoff","market_structure"})
 def test_investment_history_gate(self):
  r=evaluate_strategy(strategy_id="fundamental_investment",symbol="TEST",horizon="investment",decision_time=CUTOFF,history_sessions=119,feature_evidence=evidence_for("fundamental_investment"))
  self.assertFalse(r["history_passed"]); self.assertEqual(r["action"],"NO_TRADE")
 def test_stop_with_no_sellable_shares_is_pending(self):
  r=settlement_aware_exit_status(stop_triggered=True,position_quantity=100,broker_confirmed_sellable_quantity=0,sellable_from_date="2026-12-01",decision_date="2026-11-27",current_price="470",stress_gap_pct="5")
  self.assertEqual(r["state"],"EXIT_PENDING"); self.assertEqual(r["pending_quantity"],100); self.assertEqual(r["stress_price_scenario_not_forecast"],"446.50"); self.assertFalse(r["settlement_calendar_assumed"])
 def test_partial_sellable_position(self):
  r=settlement_aware_exit_status(stop_triggered=True,position_quantity=100,broker_confirmed_sellable_quantity=40,sellable_from_date="2026-11-27",decision_date="2026-11-27",current_price="470")
  self.assertEqual(r["state"],"PARTIAL_EXIT_POSSIBLE_REMAINDER_PENDING"); self.assertEqual(r["pending_quantity"],60)
if __name__=="__main__": unittest.main()

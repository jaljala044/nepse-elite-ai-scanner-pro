import unittest
from app.scanner_signal_qualification import qualify_scanner_signal, WEIGHTS

CUTOFF="2026-11-27T12:00:00+05:45"
def components():
 return {name:{"score":90,"status":"verified","source_id":"SRC-"+name,"evidence_id":"EV-"+name,"available_at":"2026-11-27T11:00:00+05:45"} for name in WEIGHTS}
def gates():
 return {name:{"status":"verified","source_id":"SRC-"+name,"evidence_id":"EV-"+name,"available_at":"2026-11-27T11:00:00+05:45"} for name in ("market","sector","broker","liquidity","execution","corporate_actions","source_quality")}
def plan(): return {"entry":"100","stop":"95","T1":"115","T2":"120","T3":"130","round_trip_cost_pct":"0.2","slippage_pct":"0.2","invalidation":"close below 95"}

class QualificationTests(unittest.TestCase):
 def run_case(self,**kw):
  args=dict(symbol="TEST",decision_time=CUTOFF,horizon="swing",component_evidence=components(),gates=gates(),trade_plan=plan())
  args.update(kw); return qualify_scanner_signal(**args)
 def test_complete_evidence_and_rr_qualifies_for_review(self):
  r=self.run_case()
  self.assertEqual(r["action"],"BUY")
  self.assertFalse(r["production_recommendations_enabled"])
 def test_missing_component_reduces_coverage_and_blocks(self):
  c=components(); del c["broker_footprint"]
  r=self.run_case(component_evidence=c)
  self.assertEqual(r["action"],"NO_TRADE")
  self.assertEqual(float(r["score_coverage_pct"]),90.0)
 def test_missing_gate_blocks(self):
  g=gates(); del g["execution"]
  self.assertEqual(self.run_case(gates=g)["action"],"NO_TRADE")
 def test_low_reward_risk_blocks(self):
  p=plan(); p["T1"]="106"
  self.assertIn("net_T1_reward_risk_below_2",self.run_case(trade_plan=p)["trade_plan_errors"])
 def test_future_component_is_rejected(self):
  c=components(); c["wyckoff"]["available_at"]="2026-11-27T13:00:00+05:45"
  self.assertEqual(self.run_case(component_evidence=c)["action"],"NO_TRADE")
 def test_invalid_horizon_rejected(self):
  with self.assertRaises(ValueError): self.run_case(horizon="daytrade")
 def test_naive_decision_time_rejected(self):
  with self.assertRaises(ValueError): self.run_case(decision_time="2026-11-27T12:00:00")

if __name__=="__main__": unittest.main()

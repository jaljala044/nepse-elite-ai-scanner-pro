import unittest
from app.early_market_candidates import EarlyCandidateError, classify_early_market_candidates

def snap():
 t="2026-11-26T10:00:00+05:45"
 return {"symbol":"CFCL","security_id":"SEC-CFCL","as_of_date":"2026-11-25","available_at":t,
 "broker":{"status":"verified","source_id":"BROKER_FEED","coverage":"1","available_at":t,"net_amount":"700","gross_amount":"1000","positive_net_session_ratio":"0.8"},
 "price_volume":{"status":"verified","source_id":"OHLCV","coverage":"1","available_at":t,"volume_vs_20d_average":"1.8","close_position_20d_range":"0.65","structure":"bullish_bos","volume_demand_supply":"demand_absorption"},
 "relative_strength":{"status":"verified","source_id":"RS_ENGINE","coverage":"1","available_at":t,"stock_return_1m":"0.12","index_return_1m":"0.03"},
 "sector":{"status":"verified","source_id":"SECTOR_ENGINE","coverage":"1","available_at":t,"sector_excess_return_1m":"0.04"}}

class CandidateTests(unittest.TestCase):
 def runit(self,s): return classify_early_market_candidates(s,as_of_date="2026-11-26",as_of_timestamp="2026-11-26T12:00:00+05:45")
 def test_accumulation_watch_not_buy(self):
  r=self.runit(snap()); self.assertEqual(r["classification"],"early_accumulation_candidate"); self.assertEqual(r["action"],"WATCH_FOR_CONFIRMATION"); self.assertIsNone(r["probability"])
 def test_unverified_withheld(self):
  s=snap(); s["broker"]["status"]="unverified"; self.assertEqual(self.runit(s)["action"],"NO_TRADE")
 def test_low_coverage_withheld(self):
  s=snap(); s["sector"]["coverage"]="0.8"; self.assertIn("coverage_below_threshold",self.runit(s)["reason"])
 def test_late_data_withheld(self):
  s=snap(); s["price_volume"]["available_at"]="2026-11-27T10:00:00+05:45"; self.assertEqual(self.runit(s)["status"],"withheld")
 def test_duplicate_source_diversity_withheld(self):
  s=snap(); s["sector"]["source_id"]="OHLCV"; self.assertEqual(self.runit(s)["reason"],"insufficient_independent_source_diversity")
 def test_distribution_candidate(self):
  s=snap(); s["broker"].update(net_amount="-700",positive_net_session_ratio="0.2")
  s["price_volume"].update(structure="bearish_bos",volume_demand_supply="supply_absorption",close_position_20d_range="0.2")
  s["relative_strength"].update(stock_return_1m="-0.1",index_return_1m="0.02"); s["sector"]["sector_excess_return_1m"]="-0.03"
  self.assertEqual(self.runit(s)["classification"],"distribution_risk_candidate")
 def test_naive_timestamp_rejected(self):
  s=snap(); s["available_at"]="2026-11-26T10:00:00"
  with self.assertRaises(EarlyCandidateError): self.runit(s)

if __name__=="__main__": unittest.main()

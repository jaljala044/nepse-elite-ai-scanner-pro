import unittest
from datetime import date,timedelta
from app.idpat_horizon_validation import validate_idpat_horizons

def snapshot_fixture(count=120):
    bars=[]; start=date(2026,7,1)
    for i in range(count):
        close=100+i*0.2
        bars.append({"date":(start+timedelta(days=i)).isoformat(),"open":str(close-0.5),
          "high":str(close+1),"low":str(close-1),"close":str(close),"volume":"1000"})
    return {"symbol":"AAA","price_volume":{"status":"verified","source_id":"SRC-A",
      "coverage":"1","available_at":"2026-11-27T12:00:00Z","bars":bars}}
class HorizonTests(unittest.TestCase):
    def test_four_horizons_evaluate_without_trade_action(self):
        s=snapshot_fixture(); days=[x["date"] for x in s["price_volume"]["bars"]]
        r=validate_idpat_horizons(snapshot=s,as_of_date=days[-1],as_of_timestamp="2026-11-27T13:00:00Z",
          history_validation={"research_review_allowed":True,"production_promotion_allowed":False})
        self.assertEqual(r["status"],"all_horizons_research_validated")
        self.assertEqual(set(r["horizons"]),{"t_plus_2","swing","positional","investment"})
        self.assertTrue(all(x["action"]=="NO_TRADE" for x in r["horizons"].values()))
    def test_history_gate_blocks_all(self):
        s=snapshot_fixture()
        r=validate_idpat_horizons(snapshot=s,as_of_date="2026-10-01",as_of_timestamp="2026-11-27T13:00:00Z",
          history_validation={"research_review_allowed":False})
        self.assertTrue(all(x["status"]=="withheld" for x in r["horizons"].values()))
    def test_short_history_withholds_investment(self):
        s=snapshot_fixture(60); days=[x["date"] for x in s["price_volume"]["bars"]]
        r=validate_idpat_horizons(snapshot=s,as_of_date=days[-1],as_of_timestamp="2026-11-27T13:00:00Z",
          history_validation={"research_review_allowed":True,"production_promotion_allowed":False})
        self.assertEqual(r["horizons"]["investment"]["status"],"withheld")
    def test_twenty_bars_do_not_get_filled(self):
        s=snapshot_fixture(20)
        r=validate_idpat_horizons(snapshot=s,as_of_date="2026-07-20",as_of_timestamp="2026-11-27T13:00:00Z",
          history_validation={"research_review_allowed":True,"production_promotion_allowed":False})
        self.assertTrue(all(x["status"]=="withheld" for x in r["horizons"].values()))
if __name__ == "__main__": unittest.main()

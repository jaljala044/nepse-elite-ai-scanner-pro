import unittest
from decimal import Decimal
from app.broker_context_metrics import concentration,sector_rotation

class BrokerMetricsTests(unittest.TestCase):
    def test_concentration_reconciles_both_sides(self):
        rows=[{"broker_id":"A","buy_amount":"60","sell_amount":"20"},
              {"broker_id":"B","buy_amount":"30","sell_amount":"30"},
              {"broker_id":"C","buy_amount":"10","sell_amount":"50"}]
        r=concentration(rows,matched_turnover=100)
        self.assertEqual(r["status"],"descriptive_only")
        self.assertEqual(Decimal(r["hhi"]),Decimal(".34"))
        self.assertEqual(Decimal(r["top3_share"]),1)
        self.assertEqual(Decimal(r["top5_share"]),1)
        self.assertEqual(Decimal(r["matched_turnover"]),100)
        self.assertEqual(Decimal(r["gross_side_amount"]),200)
        self.assertFalse(r["production_eligible"])
    def test_top3_top5(self):
        rows=[{"broker_id":str(i),"buy_amount":10,"sell_amount":10} for i in range(10)]
        r=concentration(rows,matched_turnover=100)
        self.assertEqual(Decimal(r["hhi"]),Decimal(".1"))
        self.assertEqual(Decimal(r["top3_share"]),Decimal(".3"))
        self.assertEqual(Decimal(r["top5_share"]),Decimal(".5"))
    def test_concentration_rejects_mismatch_and_duplicates(self):
        row={"broker_id":"A","buy_amount":100,"sell_amount":99}
        self.assertEqual(concentration([row],matched_turnover=100)["status"],"insufficient_evidence")
        with self.assertRaises(ValueError): concentration([row,row],matched_turnover=100)
    def windows(self):
        a=[{"status":"descriptive_only","broker_id":"B","security_id":s,"sector_code":s,"sessions":["2026-01-01","2026-01-02"],"gross_broker_side_amount":v} for s,v in [("H","80"),("B","20")]]
        b=[dict(r,sessions=["2026-01-03","2026-01-04"],gross_broker_side_amount="40" if r["security_id"]=="H" else "60") for r in a]
        return {"profiles":a},{"profiles":b}
    def test_rotation(self):
        a,b=self.windows()
        r=sector_rotation(a,b)
        self.assertEqual(r["status"],"descriptive_only")
        self.assertEqual({x["sector_code"]:Decimal(x["share_change"]) for x in r["rows"]},{"H":Decimal("-.4"),"B":Decimal(".4")})
        self.assertFalse(r["production_eligible"])
    def test_rotation_rejects_scope_and_membership_changes(self):
        a,b=self.windows()
        b["profiles"].pop()
        self.assertEqual(sector_rotation(a,b)["status"],"insufficient_evidence")
        a,b=self.windows()
        b["profiles"][0]["sector_code"]="NEW"
        self.assertEqual(sector_rotation(a,b)["status"],"insufficient_evidence")
        a,b=self.windows()
        b["profiles"][0]["sessions"]=a["profiles"][0]["sessions"]
        self.assertEqual(sector_rotation(a,b)["status"],"insufficient_evidence")

import unittest
from app.trade_geometry import plan_long
class TradeGeometryTests(unittest.TestCase):
    def test_unverified(self):
        self.assertIsNone(plan_long(100,95,[110])["entry"])
    def test_geometry(self):
        r=plan_long(100,95,[115,110,110,120],eligible=True)
        self.assertEqual([t["reward_risk"] for t in r["targets"]],[2,3,4])
        self.assertEqual(r["risk_pct"],5)
        self.assertEqual(r["action"],"NO TRADE")
    def test_invalid_stop(self):
        self.assertEqual(plan_long(100,101,[120],eligible=True)["status"],"invalid_geometry")
    def test_near_target(self):
        self.assertEqual(plan_long(100,95,[105,120],eligible=True)["status"],"poor_or_missing_reward_risk")

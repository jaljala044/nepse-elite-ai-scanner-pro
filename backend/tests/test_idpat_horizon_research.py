import unittest
from app.idpat_horizon_research import broker_persistence,horizon_review

class HorizonResearchTests(unittest.TestCase):
    def test_missing_flow(self):
        self.assertEqual(broker_persistence([],["2025-01-0"+str(i) for i in range(1,6)],"ABC","2025-02-01T00:00:00Z"),"UNKNOWN")
    def test_missing_bars(self):
        result=horizon_review([],"2025-02-01T00:00:00Z")
        self.assertEqual(len(result["plans"]),4)
        self.assertTrue(all(p["action"]=="NO_TRADE" and p["T1"] is None for p in result["plans"].values()))

import unittest
from copy import deepcopy
from app.smc_confluence import evaluate_confluence

def fixture():
    events=[{"type":"bos","direction":"bullish"},{"type":"liquidity_sweep","side":"low"},
            {"type":"fvg","zone_id":"z","direction":"bullish"},
            {"type":"zone_retest","zone_id":"z","direction":"bullish"}]
    return ({"status":"screened","events":events,"dealing_range":{"location":"discount"}},
            {"status":"research_only","daily_bias":"bullish","alignment":"aligned",
             "t_plus_2":{"recent_events":events,"relative_volume":1.5}})

class ConfluenceTests(unittest.TestCase):
    def test_full_research_score_not_production_signal(self):
        s,t=fixture()
        r=evaluate_confluence(s,t,eligible=True)
        self.assertEqual(r["score"],100)
        self.assertEqual(r["coverage"],100)
        self.assertIsNone(r["production_score"])
        self.assertEqual(r["action"],"NO TRADE")
    def test_missing_evidence_suppresses_score(self):
        s,t=fixture()
        t["alignment"]="unavailable"
        t["t_plus_2"]["relative_volume"]=None
        r=evaluate_confluence(s,t,eligible=True)
        self.assertEqual(r["coverage"],75)
        self.assertIsNone(r["score"])
        self.assertEqual(set(r["missing"]),{"alignment","volume"})
    def test_invalidated_zone_not_counted(self):
        s,t=fixture()
        t=deepcopy(t)
        s["events"].append({"type":"zone_invalidated","zone_id":"z"})
        r=evaluate_confluence(s,t,eligible=True)
        self.assertEqual(r["score"],80)
    def test_unverified_blocked(self):
        s,t=fixture()
        self.assertEqual(evaluate_confluence(s,t)["coverage"],0)
        self.assertIsNone(evaluate_confluence(s,t)["score"])
    def test_neutral_direction_not_scored(self):
        s,t=fixture()
        t["daily_bias"]="neutral"
        self.assertIsNone(evaluate_confluence(s,t,eligible=True)["score"])

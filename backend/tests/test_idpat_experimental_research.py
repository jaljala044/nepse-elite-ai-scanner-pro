import unittest
from datetime import datetime,timedelta,timezone
from app.idpat_experimental_research import register_plan,research_events

class IDPATResearchTests(unittest.TestCase):
    def rows(self):
        start=datetime(2025,1,1,tzinfo=timezone.utc)
        return [dict(status="verified",source_id="synthetic",observed_at=(start+timedelta(days=i)).isoformat(),available_at=(start+timedelta(days=i,hours=1)).isoformat(),open=100,high=105,low=95,close=100,volume=100,price_basis="raw") for i in range(21)]
    def test_shakeout(self):
        rows=self.rows(); rows[-1].update(low=90,close=101)
        result=research_events(rows,"2025-02-01T00:00:00Z")
        self.assertIn("SHAKEOUT_PROXY",result["events"])
        self.assertIsNone(result["score"])
        self.assertIsNone(result["original_idpat"]["OPR"])
    def test_breakout(self):
        rows=self.rows(); rows[-1].update(high=110,close=109,volume=200)
        self.assertIn("BREAKOUT_PROXY",research_events(rows,"2025-02-01T00:00:00Z")["events"])
    def test_undated_plan(self):
        p=dict(entry_low=100,entry_high=100,stop=90,target_low=120,target_high=120)
        r=register_plan(p,"2025-02-01T00:00:00Z")
        self.assertFalse(r["timestamp_gate_passed"])
        self.assertFalse(r["backtest_eligible"])
    def test_future_bar(self):
        with self.assertRaises(ValueError): research_events(self.rows(),"2025-01-15T00:00:00Z")

import unittest
from datetime import datetime,timedelta,timezone
from app.idpat_confluence_research import review_confluence
from app.idpat_walk_forward_research import walk_forward

class ConfluenceTests(unittest.TestCase):
    def rows(self,n):
        start=datetime(2025,1,1,tzinfo=timezone.utc)
        return [dict(symbol="ABC",status="verified",source_id="synthetic",observed_at=(start+timedelta(days=i)).isoformat(),available_at=(start+timedelta(days=i,hours=1)).isoformat(),open=100,high=105,low=95,close=100,volume=100,price_basis="raw") for i in range(n)]
    def test_missing_broker(self):
        r=review_confluence(self.rows(25),"2025-06-01T00:00:00Z")
        self.assertEqual(r["broker_flow"],"UNKNOWN")
        self.assertIsNone(r["plan"])
    def test_future_broker(self):
        b=dict(symbol="ABC",status="verified",source_id="synthetic",available_at="2025-07-01T00:00:00Z")
        with self.assertRaises(ValueError): review_confluence(self.rows(25),"2025-06-01T00:00:00Z",b)
    def test_folds(self):
        r=walk_forward(self.rows(125),"2025-06-01T00:00:00Z")
        self.assertEqual(r["fold_count"],1)
        self.assertLess(r["folds"][0]["train_end"],r["folds"][0]["test_start"])

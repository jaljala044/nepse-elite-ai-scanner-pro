import unittest
from datetime import date, timedelta
from app.idpat_v3 import research_features, evaluate_idpat_v3, evaluate_provisional

class IDPATFoundationTests(unittest.TestCase):
    def rows(self):
        return [dict(date=date(2025,1,1)+timedelta(days=i),open=100+i,high=102+i,low=99+i,close=101+i,volume=200 if i==20 else 100) for i in range(21)]
    def test_features(self):
        result=research_features(self.rows())
        self.assertEqual(result["status"],"research_features_ready")
        self.assertEqual(result["features"]["relative_volume20"],2)
        self.assertAlmostEqual(result["features"]["return20_pct"],100*(121/101-1))
    def test_unverified(self):
        self.assertIsNone(evaluate_idpat_v3(self.rows(),eligible=True)["score"])
        self.assertEqual(evaluate_idpat_v3(self.rows(),eligible=True)["status"],"specification_unverified")
        self.assertEqual(evaluate_idpat_v3(self.rows())["status"],"eligibility_unverified")
    def test_quality(self):
        rows=self.rows()
        rows[-1]["high"]=1
        self.assertEqual(research_features(rows)["status"],"data_quality_failed")
    def test_short_history(self):
        self.assertEqual(research_features(self.rows()[:20])["status"],"insufficient_data")

    def test_provisional(self):
        rows=self.rows()
        result=evaluate_provisional(rows,eligible=True)
        self.assertEqual(result["score"],75)
        self.assertEqual(result["method"],"nepse_provisional_v1")
        self.assertIsNone(evaluate_provisional(rows)["score"])
        self.assertEqual(evaluate_provisional(rows,eligible=True,volume_threshold=3)["score"],50)
        self.assertIsNone(evaluate_idpat_v3(rows,eligible=True)["score"])
    def test_config(self):
        with self.assertRaises(ValueError):
            evaluate_provisional(self.rows(),eligible=True,weights=(0,0,0,0))

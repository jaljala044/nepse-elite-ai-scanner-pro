import unittest
from datetime import date,timedelta
from app.advanced_technical_adapter import derive_advanced_technical

class AdvancedTechnicalTests(unittest.TestCase):
    def evaluate(self,n):
        days=[str(date(2024,1,1)+timedelta(days=i)) for i in range(n)]
        def rows(symbol,step):
            return [dict(symbol=symbol,date=d,open=100+i*step,high=101+i*step,
                         low=99+i*step,close=100+i*step,volume=1000,
                         status="verified",source_id="synthetic",basis_id="B",
                         price_basis="corporate_action_reviewed",available_at=d+"T16:00:00+05:45")
                    for i,d in enumerate(days)]
        return derive_advanced_technical(symbol="AAA",rows=rows("AAA",1),
            benchmark_rows=rows("NEPSE",0),sessions=days,assessment_time=days[-1]+"T17:00:00+05:45")
    def test_full_windows(self):
        result=self.evaluate(252)
        expected=sum(w*100*n/(351-n) for n,w in [(5,.2),(21,.3),(63,.3),(126,.2)])
        self.assertAlmostEqual(result["weighted_rs_pct"],expected)
        self.assertTrue(all(result["minervini_checks"].values()))
        self.assertIsNone(result["idpat"]["score"])
        self.assertFalse(result["production_eligible"])
    def test_short_history(self):
        result=self.evaluate(21)
        self.assertIsNone(result["weighted_rs_pct"])
        self.assertEqual(result["minervini_status"],"UNKNOWN")
        self.assertEqual(result["wyckoff_status"],"UNKNOWN")

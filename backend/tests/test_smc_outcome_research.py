import unittest
from datetime import date,timedelta
from app.smc_outcome_research import evaluate_smc_outcomes

class SMCOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.days=[str(date(2024,1,1)+timedelta(days=i)) for i in range(150)]
        self.now=self.days[-1]+"T17:00:00+05:45"
    def signal(self,i):
        return dict(signal_id=str(i),symbol="AAA",event="bos",direction="bullish",
                    status="verified",source_id="synthetic",
                    decision_time=self.days[i]+"T17:00:00+05:45",
                    available_at=self.days[i]+"T16:00:00+05:45")
    def run_review(self,signals):
        return evaluate_smc_outcomes(signals=signals,price_rows_by_symbol={},
            sessions=self.days,assessment_time=self.now,test_start=self.days[80])
    def test_purge(self):
        result=self.run_review([self.signal(0),self.signal(75),self.signal(90)])
        for horizon in result["horizons"].values():
            self.assertIn("75",horizon["purged_signal_ids"])
            self.assertEqual(horizon["test"]["results"][0]["status"],"UNKNOWN")
        self.assertIsNone(result["calibrated_score"])
    def test_future_evidence(self):
        s=self.signal(0)
        s["available_at"]=self.days[1]+"T16:00:00+05:45"
        with self.assertRaises(ValueError):
            self.run_review([s])

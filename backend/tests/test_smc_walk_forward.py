import unittest
from datetime import date,timedelta
from app.smc_walk_forward import review_breakout_failure,walk_forward_smc

class SMCWalkForwardTests(unittest.TestCase):
    def setUp(self):
        self.days=[str(date(2024,1,1)+timedelta(days=i)) for i in range(100)]
        self.now=self.days[-1]+"T17:00:00+05:45"
    def signal(self,i):
        return dict(signal_id=str(i),symbol="AAA",event="bos",direction="bullish",
                    level=100,basis_id="B",status="verified",source_id="synthetic",
                    decision_time=self.days[i]+"T17:00:00+05:45",
                    available_at=self.days[i]+"T16:00:00+05:45")
    def test_failure(self):
        rows=[dict(symbol="AAA",date=d,close=99 if i==2 else 105,basis_id="B",
                   price_basis="corporate_action_reviewed",status="verified",source_id="synthetic",
                   available_at=d+"T16:00:00+05:45") for i,d in enumerate(self.days[1:6])]
        args=dict(signal=self.signal(0),sessions=self.days,assessment_time=self.now)
        self.assertEqual(review_breakout_failure(rows=rows,**args)["failure_date"],self.days[3])
        self.assertEqual(review_breakout_failure(rows=rows[:-1],**args)["status"],"UNKNOWN")
    def test_disjoint_test_decisions(self):
        result=walk_forward_smc(signals=[self.signal(30),self.signal(60)],price_rows_by_symbol={},
            sessions=self.days,assessment_time=self.now,test_starts=[self.days[20],self.days[50]])
        ids=[[r["signal_id"] for r in f["horizons"]["t_plus_2"]["test"]["results"]] for f in result["folds"]]
        self.assertEqual(ids,[["30"],["60"]])
        self.assertIsNone(result["calibrated_score"])

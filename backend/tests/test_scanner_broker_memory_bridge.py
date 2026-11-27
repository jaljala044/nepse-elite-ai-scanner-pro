import unittest
from app.scanner_broker_memory_bridge import review_cohort
class BridgeTests(unittest.TestCase):
    def test_persistence(self):
        days=["2026-11-16","2026-11-17","2026-11-18"]
        selection=dict(symbol="API",broker_numbers=[1],status="verified",source_id="synthetic-selection",available_at="2026-11-15T16:00:00+05:45")
        inputs=[]
        for d in days:
            t=d+"T16:00:00+05:45"
            m=dict(symbol="API",session=d,status="verified",source_id="synthetic",available_at=t,coverage_complete=True)
            inputs.append(dict(session=d,manifest=m,rows=[dict(m,broker_id=1,observed_at=t,buy_turnover=100,sell_turnover=20)],price=dict(m,date=d,close=100,price_basis="corporate_action_reviewed")))
        args=dict(symbol="API",sessions=days,selection=selection,daily_inputs=inputs,decision_time=days[-1]+"T17:00:00+05:45")
        r=review_cohort(**args)
        self.assertEqual(r["histories"][0]["latest_streak"],3)
        self.assertIn("ACCUMULATION_PATTERN",r["histories"][0]["observations"][-1]["flags"])
        args["daily_inputs"]=inputs[::2]
        self.assertEqual(review_cohort(**args)["histories"][0]["latest_streak"],1)

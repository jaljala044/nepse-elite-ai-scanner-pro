import unittest
from app.part5_exit_retry import retry_exit

class ExitRetryTests(unittest.TestCase):
    def test_pending_stop_retries_after_settlement_and_missing_session(self):
        days=["2025-01-02","2025-01-05","2025-01-06","2025-01-07"]
        bars={days[0]:dict(open=100,high=101,low=94,close=95,volume=1000),
              days[3]:dict(open=93,high=96,low=92,close=95,volume=1000)}
        result=retry_exit(days,bars,{days[3]:dict(lower=90,upper=110)},
            settled_on=days[1],deadline=days[3],stop=95,target=110)
        self.assertEqual(result["status"],"closed_scenario")
        self.assertEqual(result["price"],93)
        self.assertEqual(result["attempts"][0]["status"],"missing_evidence")

    def test_limit_down_remains_unresolved(self):
        day="2025-01-07"
        bar=dict(open=90,high=90,low=90,close=90,volume=1000)
        result=retry_exit([day],{day:bar},{day:dict(lower=90,upper=110)},
            settled_on="2025-01-06",deadline=day,stop=95,target=110,pending_stop=True)
        self.assertEqual(result["status"],"open_unresolved")
        self.assertIsNone(result["price"])

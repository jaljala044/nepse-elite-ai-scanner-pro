import unittest
from app.scanner_broker_normalization import normalize_broker_day
class BrokerTests(unittest.TestCase):
    def test_cohort(self):
        t="2026-11-19T16:00:00+05:45"
        m=dict(symbol="API",session="2026-11-19",status="verified",source_id="synthetic",available_at=t,coverage_complete=True)
        r=dict(m,broker_id="1",observed_at=t,buy_turnover="100",sell_turnover="20")
        args=dict(symbol="API",session=m["session"],rows=[r],manifest=m,decision_time=t)
        self.assertEqual(normalize_broker_day(cohort=["1"],**args)["buy_turnover"],"100")
        self.assertFalse(normalize_broker_day(cohort=["1","2"],**args)["coverage_complete"])

import unittest
from app.portfolio_broker_alerts import review_holding_broker_flow

class PortfolioBrokerAlertTests(unittest.TestCase):
    def setUp(self):
        self.now="2025-02-01T16:00:00+05:45"
        self.evidence=dict(symbol="AAA",status="verified",source_id="synthetic",available_at=self.now)
        self.records=[dict(self.evidence,window=w,start_at=start,end_at="2025-02-01T15:00:00+05:45",
                           complete=True,broker_numbers=[42,58],buy_turnover=20,sell_turnover=80)
                      for w,start in [("1D","2025-02-01T11:00:00+05:45"),
                                      ("1W","2025-01-26T11:00:00+05:45"),
                                      ("1M","2025-01-01T11:00:00+05:45")]]
    def review(self,records=None,price=None):
        return review_holding_broker_flow(symbol="AAA",records=self.records if records is None else records,
                                         assessment_time=self.now,price_evidence=price)
    def test_distribution(self):
        self.assertEqual(self.review()["action"],"DISTRIBUTION_RISK_REVIEW")
    def test_exit(self):
        self.assertEqual(self.review(price=dict(self.evidence,close=90,support=100))["action"],"EXIT_REVIEW")
    def test_accumulation(self):
        self.assertEqual(self.review([dict(r,buy_turnover=80,sell_turnover=20) for r in self.records])["action"],"ACCUMULATION_WATCH")
    def test_missing_window(self):
        self.assertEqual(self.review(self.records[:2])["action"],"UNKNOWN")
    def test_different_cohort(self):
        self.assertEqual(self.review(self.records[:2]+[dict(self.records[2],broker_numbers=[34])])["action"],"UNKNOWN")
    def test_future_evidence(self):
        with self.assertRaisesRegex(ValueError,"lookahead"):
            self.review([dict(self.records[0],available_at="2025-02-02T16:00:00+05:45")])

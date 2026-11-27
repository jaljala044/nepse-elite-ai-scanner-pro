import unittest
from app.broker_pattern_outcomes import evaluate_broker_patterns

class BrokerOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.days=["2025-01-05","2025-01-06","2025-01-07","2025-01-08"]
        self.signal=dict(signal_id="S1",symbol="AAA",pattern="ACCUMULATION_PATTERN",
            status="verified",source_id="synthetic",decision_time=self.days[0]+"T17:00:00+05:45",
            available_at=self.days[0]+"T16:00:00+05:45")
        self.rows=[dict(date=d,close=p,status="verified",source_id="synthetic",
            available_at=d+"T16:00:00+05:45",price_basis="corporate_action_reviewed",basis_id="B")
            for d,p in zip(self.days,[90,100,105,110])]
    def evaluate(self,signals=None,rows=None):
        return evaluate_broker_patterns(signals=[self.signal] if signals is None else signals,
            price_rows_by_symbol={"AAA":self.rows if rows is None else rows},
            sessions=self.days,assessment_time=self.days[-1]+"T17:00:00+05:45",horizon=2)
    def test_return_and_reporting_floor(self):
        result=self.evaluate()
        self.assertAlmostEqual(result["results"][0]["forward_return"],.1)
        self.assertTrue(result["results"][0]["direction_hit"])
        self.assertIsNone(result["metrics"]["ACCUMULATION_PATTERN"]["directional_hit_rate"])
    def test_gap(self):
        self.assertEqual(self.evaluate(rows=self.rows[:2]+self.rows[3:])["results"][0]["status"],"UNKNOWN")
    def test_basis_mismatch(self):
        self.assertEqual(self.evaluate(rows=self.rows[:3]+[dict(self.rows[3],basis_id="C")])["results"][0]["status"],"UNKNOWN")
    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError,"duplicate_signal"):
            self.evaluate(signals=[self.signal,self.signal])
    def test_lookahead(self):
        with self.assertRaisesRegex(ValueError,"pattern_lookahead"):
            self.evaluate(signals=[dict(self.signal,available_at=self.days[1]+"T16:00:00+05:45")])

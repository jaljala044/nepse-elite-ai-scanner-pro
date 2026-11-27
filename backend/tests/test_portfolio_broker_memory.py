import unittest
from app.portfolio_broker_memory import replay_broker_patterns

class BrokerMemoryTests(unittest.TestCase):
    def setUp(self):
        self.days=["2025-01-05","2025-01-06","2025-01-07","2025-01-08"]
        self.rows=[dict(symbol="AAA",broker_numbers=[42,58],date=d,
                        status="verified",source_id="synthetic-"+d,
                        available_at=d+"T16:00:00+05:45",complete=True,
                        buy_turnover=80,sell_turnover=20,close=100+i)
                   for i,d in enumerate(self.days)]
    def replay(self,rows):
        return replay_broker_patterns(records=rows,sessions=self.days,
            assessment_time="2025-01-08T17:00:00+05:45")["histories"][0]
    def test_accumulation(self):
        self.assertIn("ACCUMULATION_PATTERN",self.replay(self.rows)["observations"][2]["flags"])
    def test_distribution(self):
        rows=[dict(r,buy_turnover=20,sell_turnover=80) for r in self.rows]
        self.assertIn("DISTRIBUTION_PATTERN",self.replay(rows)["observations"][2]["flags"])
    def test_reversal_and_strength(self):
        rows=self.rows[:3]+[dict(self.rows[3],buy_turnover=20,sell_turnover=80)]
        flags=self.replay(rows)["observations"][-1]["flags"]
        self.assertIn("FLOW_REVERSAL",flags)
        self.assertIn("SELLING_INTO_STRENGTH",flags)
    def test_gap(self):
        result=self.replay(self.rows[:1]+self.rows[2:])
        self.assertEqual(result["latest_streak"],2)
        self.assertEqual(result["coverage"],.75)
    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError,"duplicate_observation"):
            self.replay(self.rows+[self.rows[0]])
    def test_future(self):
        with self.assertRaisesRegex(ValueError,"lookahead"):
            self.replay([dict(self.rows[0],available_at="2025-01-09T16:00:00+05:45")])

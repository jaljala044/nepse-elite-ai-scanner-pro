import unittest
from app.broker_structure_confluence import compare_broker_structure

class BrokerStructureTests(unittest.TestCase):
    def setUp(self):
        self.days=["2025-01-05","2025-01-06","2025-01-07","2025-01-08","2025-01-09"]
        self.signals=[dict(signal_id=s,symbol="AAA",pattern="ACCUMULATION_PATTERN",
            status="verified",source_id="synthetic",decision_time="2025-01-06T17:00:00+05:45",
            available_at="2025-01-06T16:00:00+05:45") for s in ("A","B","C")]
        self.confirmation=dict(signal_id="A",symbol="AAA",status="verified",source_id="synthetic",
            available_at="2025-01-06T16:00:00+05:45",
            wyckoff="BULLISH",smc="BULLISH",volume="BULLISH",relative_strength="BULLISH",sector="BULLISH")
    def run_comparison(self,confirmations):
        return compare_broker_structure(signals=self.signals,confirmations=confirmations,
            price_rows_by_symbol={},sessions=self.days,test_start=self.days[1],
            assessment_time=self.days[-1]+"T17:00:00+05:45",horizon=1)
    def test_selection(self):
        result=self.run_comparison([self.confirmation,dict(self.confirmation,signal_id="B",sector="NEUTRAL")])
        self.assertEqual(result["confirmed_signal_ids"],["A"])
        self.assertEqual(result["unknown_confirmation_ids"],["C"])
        self.assertEqual(len(result["complete_evidence_baseline"]["test"]["results"]),2)
        self.assertFalse(result["execution_eligible"])
    def test_future(self):
        with self.assertRaisesRegex(ValueError,"lookahead"):
            self.run_comparison([dict(self.confirmation,available_at="2025-01-07T16:00:00+05:45")])
    def test_unknown(self):
        self.assertEqual(self.run_comparison([dict(self.confirmation,smc="UNKNOWN")])["confirmed_signal_ids"],[])
    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError,"duplicate_confirmation"):
            self.run_comparison([self.confirmation,self.confirmation])

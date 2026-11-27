import unittest
from app.scanner_broker_outcome_bridge import evaluate_cohort_history
class OutcomeTests(unittest.TestCase):
    def test_empty(self):
        r=evaluate_cohort_history(decisions=[],price_rows_by_symbol={},sessions=["2026-11-16","2026-11-17"],assessment_time="2026-11-18T17:00:00+05:45",test_start="2026-11-17")
        self.assertEqual(r["decision_count"],0)
        self.assertEqual(r["signals"],[])
        self.assertFalse(r["production_eligible"])

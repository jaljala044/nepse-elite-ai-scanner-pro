import unittest
from app.full_stack_research_validation import build_full_stack_research_validation

class FullStackTests(unittest.TestCase):
    def test_unadmitted_history_blocks_everything(self):
        r=build_full_stack_research_validation(records=[],decision_time="2026-11-27T12:00:00Z",
            evidence_pipeline={"research_review_allowed":False})
        self.assertEqual(r["status"],"blocked_missing_admitted_nepse_history")
        self.assertEqual(r["action"],"NO_TRADE")
        self.assertIsNone(r["overall_score"])
    def test_missing_evidence_pipeline_blocks(self):
        r=build_full_stack_research_validation(records=[],decision_time="2026-11-27T12:00:00Z")
        self.assertFalse(r["production_recommendations_enabled"])
if __name__=="__main__": unittest.main()

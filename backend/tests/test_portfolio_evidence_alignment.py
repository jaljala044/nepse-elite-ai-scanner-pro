import unittest
from app.portfolio_evidence_alignment import review_evidence_alignment

class EvidenceAlignmentTests(unittest.TestCase):
    def inputs(self):
        days=["2025-01-05","2025-01-06"]
        evidence=dict(status="verified",source_id="synthetic",available_at="2025-01-05T09:00:00+05:45")
        return dict(sessions=days,assessment_time="2025-01-05T20:00:00+00:00",as_of_date=days[-1],
            calendar_evidence=dict(evidence,sessions=days),
            decisions=[dict(decision_id="D",decision_time="2025-01-05T11:00:00+05:45",
                evidence=[dict(evidence,observed_at="2025-01-05T08:00:00+05:45")])])
    def test_nepal_local_date(self):
        self.assertTrue(review_evidence_alignment(**self.inputs())["all_decisions_passed"])
    def test_future_evidence(self):
        x=self.inputs()
        x["decisions"][0]["evidence"][0]["available_at"]="2025-01-05T12:00:00+05:45"
        self.assertFalse(review_evidence_alignment(**x)["all_decisions_passed"])
    def test_future_observation(self):
        x=self.inputs()
        x["decisions"][0]["evidence"][0]["observed_at"]="2025-01-05T12:00:00+05:45"
        self.assertFalse(review_evidence_alignment(**x)["all_decisions_passed"])
    def test_calendar_mismatch(self):
        x=self.inputs()
        x["calendar_evidence"]["sessions"]=[]
        with self.assertRaisesRegex(ValueError,"calendar_evidence_mismatch"):
            review_evidence_alignment(**x)
    def test_empty_evidence(self):
        x=self.inputs()
        x["decisions"][0]["evidence"]=[]
        self.assertFalse(review_evidence_alignment(**x)["all_decisions_passed"])

import unittest
from app.p4_29_evidence_intake_matrix import build_evidence_request_inventory, reconcile_event_source_matrix

class EvidenceIntakeMatrixTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = {
            "N1": {"artifact_id":"N1","publisher_id":"nepse","source_tier":"primary_nepse_or_cdsc","sha256":"a"*64,"event_ids":["CA1"]},
            "S1": {"artifact_id":"S1","publisher_id":"sharesansar","source_tier":"independent_secondary","sha256":"b"*64,"event_ids":["CA1"]},
        }
    def assertion(self, aid, publisher, tier, digest):
        return {"event_id":"CA1","artifact_id":aid,"publisher_id":publisher,"source_tier":tier,"sha256":digest,
                "available_at":"2026-01-01T00:00:00+05:45","effective_at":"2026-01-02T00:00:00+05:45",
                "symbol_or_security_id":"ABC","event_type":"BONUS","announced_at":"2025-12-20",
                "ex_date":"2026-01-02","status":"verified","factor":"1.1","factor_method":"approved_policy"}
    def test_inventory_marks_missing_real_evidence(self):
        result = build_evidence_request_inventory(required_events=[{"event_id":"CA1"},{"event_id":"CA2"}], archived_artifacts=[])
        self.assertEqual(result["unresolved_event_ids"], ["CA1","CA2"])
    def test_inventory_never_claims_review_complete(self):
        result = build_evidence_request_inventory(required_events=[{"event_id":"CA1"}], archived_artifacts=[self.artifacts["N1"]])
        self.assertEqual(result["requests"][0]["status"], "EVIDENCE_PRESENT_REVIEW_REQUIRED")
    def test_two_publishers_and_primary_are_review_ready_not_admitted(self):
        rows=[self.assertion("N1","nepse","primary_nepse_or_cdsc","a"*64),self.assertion("S1","sharesansar","independent_secondary","b"*64)]
        result=reconcile_event_source_matrix(assertions=rows,verified_artifacts=self.artifacts,required_event_ids=["CA1"],decision_cutoff="2026-11-28T12:00:00+05:45")
        self.assertEqual(result["status"],"REVIEW_READY")
        self.assertFalse(result["price_adjustment_admission_allowed"])
    def test_conflicting_source_facts_block(self):
        a=self.assertion("N1","nepse","primary_nepse_or_cdsc","a"*64)
        b=self.assertion("S1","sharesansar","independent_secondary","b"*64); b["factor"]="1.2"
        result=reconcile_event_source_matrix(assertions=[a,b],verified_artifacts=self.artifacts,required_event_ids=["CA1"],decision_cutoff="2026-11-28T12:00:00+05:45")
        self.assertEqual(result["events"][0]["status"],"BLOCKED")
    def test_unverified_artifact_blocks(self):
        row=self.assertion("UNKNOWN","x","primary_nepse_or_cdsc","c"*64)
        result=reconcile_event_source_matrix(assertions=[row],verified_artifacts=self.artifacts,required_event_ids=["CA1"],decision_cutoff="2026-11-28T12:00:00+05:45")
        self.assertEqual(result["status"],"BLOCKED")
    def test_future_assertion_blocks(self):
        row=self.assertion("N1","nepse","primary_nepse_or_cdsc","a"*64); row["available_at"]="2026-12-01T00:00:00+05:45"
        result=reconcile_event_source_matrix(assertions=[row],verified_artifacts=self.artifacts,required_event_ids=["CA1"],decision_cutoff="2026-11-28T12:00:00+05:45")
        self.assertEqual(result["status"],"BLOCKED")

if __name__ == "__main__":
    unittest.main()

import hashlib, unittest
from app.nepse_verified_bundle import build_verified_historical_bundle

class VerifiedBundleTests(unittest.TestCase):
    def test_missing_required_data_does_not_promote_bundle(self):
        result=build_verified_historical_bundle(captured_files={},start_date="2025-01-01",
            end_date="2025-01-10",decision_cutoff="2025-01-11T10:00:00+05:45")
        self.assertFalse(result["research_panel_assembly_allowed"])
        self.assertIn(result["bundle_status"],{"PARTIAL","BLOCKED"})
        self.assertFalse(result["production_enabled"])

    def test_manifest_hash_is_deterministic_and_raw_hash_is_preserved(self):
        # A valid captured calendar is intentionally insufficient without the other required datasets.
        raw=b"session_date,session_status\n2025-01-02,OPEN\n"
        item={"raw_bytes":raw,"source_id":"calendar-feed","publisher":"Publisher A",
            "source_uri":"https://example.invalid/calendar.csv","evidence_id":"CAL-1",
            "captured_at":"2025-01-03T10:00:00+05:45","rights_status":"approved",
            "registry_review_id":"review-1"}
        kwargs=dict(captured_files={"session_calendar":[item]},start_date="2025-01-01",
            end_date="2025-01-10",decision_cutoff="2025-01-11T10:00:00+05:45")
        first=build_verified_historical_bundle(**kwargs)
        second=build_verified_historical_bundle(**kwargs)
        self.assertEqual(first["dataset_bundle_sha256"],second["dataset_bundle_sha256"])
        self.assertEqual(first["files"][0]["raw_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertFalse(first["research_panel_assembly_allowed"])

if __name__=="__main__": unittest.main()

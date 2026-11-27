import hashlib, unittest
from app.nepse_source_registry import validate_source_registry, build_source_capture_run

def source(**extra):
    value={"source_id":"src-1","publisher_id":"pub-1","publisher_group":"exchange",
        "publisher_name":"Exchange feed","canonical_uri":"https://data.example.org/",
        "authority_type":"exchange_official","dataset_kinds":["session_calendar"],
        "status":"approved","review_id":"review-1","reviewed_at":"2025-01-01T00:00:00+05:45"}
    value.update(extra); return value

class SourceRegistryTests(unittest.TestCase):
    def test_registry_rejects_duplicate_source_and_publisher_ids(self):
        result=validate_source_registry([source(),source(source_id="src-2",publisher_id="pub-2")])
        self.assertEqual(result["valid_count"],1)
        self.assertEqual(result["rejected_count"],1)

    def test_capture_requires_approved_matching_host_and_validated_bytes(self):
        raw=b"session_date,session_status\n2025-01-02,OPEN\n"
        result=build_source_capture_run(registry=[source()],captures=[{
            "source_id":"src-1","dataset_kind":"session_calendar","source_uri":"https://data.example.org/calendar.csv",
            "raw_bytes":raw,"evidence_id":"cal-1","captured_at":"2025-01-03T00:00:00+05:45",
            "rights_status":"approved"}],decision_cutoff="2025-01-04T00:00:00+05:45")
        self.assertEqual(result["capture_count"],1)
        self.assertEqual(result["receipts"][0]["raw_sha256"],hashlib.sha256(raw).hexdigest())

    def test_unapproved_host_and_duplicate_payload_are_rejected(self):
        raw=b"session_date,session_status\n2025-01-02,OPEN\n"
        registry=[source(),source(source_id="src-2",publisher_id="pub-2",publisher_group="third-party",
            publisher_name="Second",canonical_uri="https://other.example.org/")]
        common={"dataset_kind":"session_calendar","raw_bytes":raw,"evidence_id":"same",
            "captured_at":"2025-01-03T00:00:00+05:45","rights_status":"approved"}
        result=build_source_capture_run(registry=registry,captures=[
            {"source_id":"src-1","source_uri":"https://evil.example.org/a.csv",**common},
            {"source_id":"src-1","source_uri":"https://data.example.org/a.csv",**common},
            {"source_id":"src-2","source_uri":"https://other.example.org/a.csv",**common}],
            decision_cutoff="2025-01-04T00:00:00+05:45")
        self.assertEqual(result["capture_count"],1)
        self.assertEqual(result["rejected_count"],2)
        self.assertTrue(any(x.get("cross_publisher_duplicate") for x in result["rejected"]))

if __name__=="__main__": unittest.main()

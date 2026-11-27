import unittest
from app.nepse_source_connectors import acquire_registered_capture

def registry():
    return [{"source_id":"src","publisher_id":"pub","publisher_group":"exchange",
        "publisher_name":"Official data","canonical_uri":"https://data.example.org/",
        "authority_type":"exchange_official","dataset_kinds":["session_calendar"],
        "status":"approved","review_id":"r1","reviewed_at":"2025-01-01T00:00:00+05:45"}]

def transport(body=b"session_date,session_status\n2025-01-02,OPEN\n", **overrides):
    result={"status":200,"final_url":"https://data.example.org/calendar.csv",
        "headers":{"Content-Length":str(len(body)),"Content-Type":"text/csv"},"body":body}
    result.update(overrides)
    return lambda uri, **kwargs: result

class SourceConnectorTests(unittest.TestCase):
    def test_fetches_and_registers_validated_capture(self):
        result=acquire_registered_capture(registry=registry(),source_id="src",
            dataset_kind="session_calendar",endpoint_uri="https://data.example.org/calendar.csv",
            evidence_id="e1",captured_at="2025-01-03T00:00:00+05:45",
            decision_cutoff="2025-01-04T00:00:00+05:45",rights_status="approved",
            transport=transport())
        self.assertTrue(result["network_retrieval_performed"])
        self.assertEqual(result["receipt"]["row_count"],1)
        self.assertEqual(result["receipt"]["raw_byte_count"],len(result["raw_bytes"]))

    def test_rejects_unregistered_host_and_redirect(self):
        args=dict(registry=registry(),source_id="src",dataset_kind="session_calendar",
            evidence_id="e1",captured_at="2025-01-03T00:00:00+05:45",
            decision_cutoff="2025-01-04T00:00:00+05:45",rights_status="approved",
            transport=transport())
        with self.assertRaisesRegex(ValueError,"endpoint_host_not_registered"):
            acquire_registered_capture(endpoint_uri="https://evil.example.org/a.csv",**args)
        with self.assertRaisesRegex(ValueError,"redirect_or_final_host_mismatch"):
            acquire_registered_capture(endpoint_uri="https://data.example.org/a.csv",
                **{**args,"transport":transport(final_url="https://evil.example.org/a.csv")})

    def test_rejects_http_error_oversized_body_and_bad_content_length(self):
        args=dict(registry=registry(),source_id="src",dataset_kind="session_calendar",
            endpoint_uri="https://data.example.org/a.csv",evidence_id="e1",
            captured_at="2025-01-03T00:00:00+05:45",decision_cutoff="2025-01-04T00:00:00+05:45",
            rights_status="approved")
        with self.assertRaisesRegex(ValueError,"http_status_not_200"):
            acquire_registered_capture(**args,transport=transport(status=503))
        with self.assertRaisesRegex(ValueError,"exceeds_max_bytes"):
            acquire_registered_capture(**args,max_bytes=5,transport=transport())
        with self.assertRaisesRegex(ValueError,"content_length_mismatch"):
            acquire_registered_capture(**args,transport=transport(headers={"Content-Length":"2"}))

if __name__=="__main__": unittest.main()

import hashlib, tempfile, unittest
from app.nepse_source_intake import ingest_trusted_nepse_ohlcv

class SourceIntakeTests(unittest.TestCase):
    def test_unapproved_registry_fails_before_capture(self):
        with tempfile.TemporaryDirectory() as root:
            r=ingest_trusted_nepse_ohlcv(raw_bytes=b"a,b\n1,2\n",
                registry_record={},source_id="S",source_uri="https://example.invalid/data",
                publisher="Example",captured_at="2026-11-27T10:00:00Z",
                published_at="2026-11-27T09:00:00Z",decision_cutoff="2026-11-27T12:00:00Z",
                expected_symbols={"AAA":"SEC-1"},verified_session_status={"2026-11-26":"confirmed_trading_session"},
                adjustment_basis="raw",output_root=root)
            self.assertEqual(r["status"],"blocked")
            self.assertFalse(r["research_review_allowed"])
    def test_registry_hash_mismatch_fails_closed(self):
        record={"source_id":"S","publisher":"Example","source_uri":"https://example.invalid/data",
          "rights_status":"approved","source_validation_status":"verified","finality_status":"final",
          "registry_status":"approved","review_id":"REV-1","reviewed_at":"2026-11-27T10:00:00Z",
          "signature_status":"independently_verified","expected_sha256":"0"*64}
        with tempfile.TemporaryDirectory() as root:
            r=ingest_trusted_nepse_ohlcv(raw_bytes=b"csv",registry_record=record,
                source_id="S",source_uri=record["source_uri"],publisher="Example",
                captured_at="2026-11-27T10:00:00Z",published_at="2026-11-27T09:00:00Z",
                decision_cutoff="2026-11-27T12:00:00Z",expected_symbols={"AAA":"SEC-1"},
                verified_session_status={"2026-11-26":"confirmed_trading_session"},
                adjustment_basis="raw",output_root=root)
            self.assertEqual(r["status"],"blocked")
            self.assertIn("registry_sha256_mismatch",r["errors"])
if __name__=="__main__": unittest.main()

import hashlib
import unittest
from app.historical_pilot_capture import validate_official_capture_manifest

class OfficialCaptureManifestTests(unittest.TestCase):
    def fixture(self):
        raw=b"symbol,price\nAAA,100\n"
        return raw, {"source_id":"NEPSE-FS","publisher_id":"NEPSE","request_url":"https://api.nepalstock.com/floorsheet?date=2025-01-02","captured_at":"2025-01-02T16:00:00+05:45","available_at":"2025-01-02T16:00:00+05:45","window_start":"2025-01-02T00:00:00+05:45","window_end":"2025-01-02T23:59:00+05:45","pages":[{"page_number":1,"payload_id":"p1","raw_sha256":hashlib.sha256(raw).hexdigest(),"http_status":200,"final_page":True}],"expected_page_count":1,"capture_complete":True,"response_content_type":"text/csv","capture_id":"CAP-1"}
    def test_valid_capture_hashes_exact_bytes(self):
        raw,m=self.fixture()
        r=validate_official_capture_manifest(m,{"p1":raw},approved_registry=[{"source_id":"NEPSE-FS","publisher_id":"NEPSE","review_status":"approved","allowed_hosts":["api.nepalstock.com"]}],decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(r["status"],"CAPTURE_VALIDATED")
        self.assertFalse(r["backtest_admission_allowed"])
    def test_payload_tampering_blocks(self):
        raw,m=self.fixture()
        r=validate_official_capture_manifest(m,{"p1":raw+b"x"},approved_registry=[{"source_id":"NEPSE-FS","publisher_id":"NEPSE","review_status":"approved","allowed_hosts":["api.nepalstock.com"]}],decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(r["status"],"CAPTURE_BLOCKED")
        self.assertIn("raw_payload_sha256_mismatch",[x["reason"] for x in r["errors"]])
    def test_incomplete_pages_block(self):
        raw,m=self.fixture(); m["expected_page_count"]=2
        r=validate_official_capture_manifest(m,{"p1":raw},approved_registry=[{"source_id":"NEPSE-FS","publisher_id":"NEPSE","review_status":"approved","allowed_hosts":["api.nepalstock.com"]}],decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertIn("pagination_incomplete_or_noncontiguous",[x["reason"] for x in r["errors"]])
    def test_unapproved_host_blocks(self):
        raw,m=self.fixture(); m["request_url"]="http://evil.example/data"
        r=validate_official_capture_manifest(m,{"p1":raw},approved_registry=[{"source_id":"NEPSE-FS","publisher_id":"NEPSE","review_status":"approved","allowed_hosts":["api.nepalstock.com"]}],decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertIn("request_url_not_https_allowlisted",[x["reason"] for x in r["errors"]])

if __name__=="__main__": unittest.main()

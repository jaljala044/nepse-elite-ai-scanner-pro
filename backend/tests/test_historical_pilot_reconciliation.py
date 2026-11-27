import hashlib
import unittest
from app.historical_pilot_reconciliation import reconcile_lifecycle_pilot_sources

class PilotSourceReconciliationTests(unittest.TestCase):
    def fixture(self):
        raw=b"contract_id,security_id,trade_date,quantity,price\nC-1,SEC-1,2025-01-02,100,10\n"
        digest=hashlib.sha256(raw).hexdigest()
        manifest={"source_id":"SRC-1","publisher_id":"PUB-1","request_url":"https://official.example/data.csv","captured_at":"2025-01-03T10:00:00+05:45","available_at":"2025-01-03T10:00:00+05:45","window_start":"2025-01-02T00:00:00+05:45","window_end":"2025-01-02T23:59:59+05:45","pages":[{"page_number":1,"payload_id":"p1","raw_sha256":digest,"http_status":200,"final_page":True}],"expected_page_count":1,"capture_complete":True,"response_content_type":"text/csv","capture_id":"CAP-1"}
        cohort=[{"symbol":"AAA","reported_first_trade_date":"2025-01-02"}]
        evidence=[{"symbol":"AAA","source_type":"nepse_official_floorsheet","contract_id":"C-1","security_id":"SEC-1","raw_sha256":digest,"source_record_id":"REC-1","trade_date":"2025-01-02","quantity":100,"price":10,"captured_at":"2025-01-03T10:00:00+05:45","available_at":"2025-01-03T10:00:00+05:45","finality":"final","record_status":"verified","capture_complete":True}]
        registry=[{"source_id":"SRC-1","publisher_id":"PUB-1","review_status":"approved","allowed_hosts":["official.example"]}]
        return raw,manifest,cohort,evidence,registry
    def test_valid_capture_and_first_trade_reconcile(self):
        raw,m,c,e,r=self.fixture()
        out=reconcile_lifecycle_pilot_sources(cohort_rows=c,capture_artifacts={"first_day":{"manifest":m,"payloads":{"p1":raw}}},required_capture_keys=["first_day"],approved_registry=r,official_first_trade_rows=e,decision_cutoff="2025-01-04T00:00:00+05:45")
        self.assertEqual(out["status"],"SOURCE_EVIDENCE_RECONCILED")
        self.assertTrue(out["source_reconciliation_passed"])
    def test_missing_capture_blocks(self):
        _,_,c,e,r=self.fixture()
        out=reconcile_lifecycle_pilot_sources(cohort_rows=c,capture_artifacts={},required_capture_keys=["first_day"],approved_registry=r,official_first_trade_rows=e,decision_cutoff="2025-01-04T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["missing_capture_keys"],["first_day"])
    def test_wrong_first_trade_date_blocks(self):
        raw,m,c,e,r=self.fixture(); c[0]["reported_first_trade_date"]="2025-01-03"
        out=reconcile_lifecycle_pilot_sources(cohort_rows=c,capture_artifacts={"first_day":{"manifest":m,"payloads":{"p1":raw}}},required_capture_keys=["first_day"],approved_registry=r,official_first_trade_rows=e,decision_cutoff="2025-01-04T00:00:00+05:45")
        self.assertFalse(out["first_trade_gate_passed"])
    def test_duplicate_capture_id_blocks(self):
        raw,m,c,e,r=self.fixture()
        out=reconcile_lifecycle_pilot_sources(cohort_rows=c,capture_artifacts={"a":{"manifest":m,"payloads":{"p1":raw}},"b":{"manifest":m,"payloads":{"p1":raw}}},required_capture_keys=["a","b"],approved_registry=r,official_first_trade_rows=e,decision_cutoff="2025-01-04T00:00:00+05:45")
        self.assertEqual(len(out["duplicate_capture_ids"]),1)
        self.assertFalse(out["capture_gate_passed"])

if __name__=="__main__": unittest.main()

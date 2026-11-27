import unittest
from app.historical_pilot_source_contract import validate_historical_source_contract
from app.historical_pilot_capture_runner import capture_registered_source_pages
from app.historical_pilot_capture_package import accept_historical_capture_package


class CapturePackageTests(unittest.TestCase):
    def setup_package(self):
        contract={"source_id":"SRC","publisher_id":"PUB","dataset_kind":"official_eod_ohlcv","endpoint_url":"https://data.example.test/eod","allowed_hosts":["data.example.test"],"allowed_content_types":["text/csv"],"window_start":"2025-01-01T00:00:00+05:45","window_end":"2025-01-31T23:59:00+05:45","review_status":"approved","approved_by_human":True,"reviewer_id":"reviewer-1","reviewed_at":"2025-02-01T09:00:00+05:45","authority_evidence_ref":"DOC-1","licence_reviewed":True,"access_policy_reviewed":True,"authentication_mode":"public","page_parameter":"page","terminal_signal":"has_more_false","max_pages":50,"minimum_request_interval_seconds":1.0,"capture_id":"CAP-1"}
        approved=validate_historical_source_contract(contract=contract,decision_cutoff="2025-02-02T00:00:00+05:45")
        raw=b"symbol,date,open,high,low,close,volume\nAAA,2025-01-02,10,12,9,11,100\n"
        def fetch(url):
            return {"status_code":200,"final_url":url,"content_type":"text/csv","body":raw,"has_more":False,"available_at":"2025-02-01T10:00:00+05:45"}
        result=capture_registered_source_pages(source_spec=approved["capture_spec"],fetch_page=fetch,captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        return approved,result,result["payloads"]
    def test_approved_complete_capture_passes_strict_package_acceptance(self):
        approved,result,payloads=self.setup_package()
        out=accept_historical_capture_package(source_contract_report=approved,capture_result=result,payloads=payloads,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION")
        self.assertEqual(out["verified_page_count"],1)
        self.assertFalse(out["backtest_admission_allowed"])
    def test_contract_mismatch_blocks_package(self):
        approved,result,payloads=self.setup_package()
        result["manifest"]["capture_id"]="OTHER"
        out=accept_historical_capture_package(source_contract_report=approved,capture_result=result,payloads=payloads,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"PACKAGE_BLOCKED")
    def test_missing_payload_blocks_package(self):
        approved,result,payloads=self.setup_package()
        out=accept_historical_capture_package(source_contract_report=approved,capture_result=result,payloads={},decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"PACKAGE_BLOCKED")
    def test_unapproved_contract_never_accepts_capture(self):
        approved,result,payloads=self.setup_package()
        approved["status"]="CONTRACT_BLOCKED"
        out=accept_historical_capture_package(source_contract_report=approved,capture_result=result,payloads=payloads,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"PACKAGE_BLOCKED")


if __name__=="__main__": unittest.main()

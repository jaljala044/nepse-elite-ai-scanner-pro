import unittest
from app.historical_pilot_source_contract import validate_historical_source_contract
from app.historical_pilot_source_capture import capture_approved_historical_source


class ApprovedSourceCaptureTests(unittest.TestCase):
    def contract(self):
        return {"source_id":"SRC","publisher_id":"PUB","dataset_kind":"official_eod_ohlcv","endpoint_url":"https://data.example.test/eod","allowed_hosts":["data.example.test"],"allowed_content_types":["text/csv"],"window_start":"2025-01-01T00:00:00+05:45","window_end":"2025-01-31T23:59:00+05:45","review_status":"approved","approved_by_human":True,"reviewer_id":"reviewer-1","reviewed_at":"2025-02-01T09:00:00+05:45","authority_evidence_ref":"DOC-1","licence_reviewed":True,"access_policy_reviewed":True,"authentication_mode":"public","page_parameter":"page","terminal_signal":"has_more_false","max_pages":1,"minimum_request_interval_seconds":1.0,"capture_id":"CAP-1"}
    def test_only_approved_contract_runs_and_uses_reviewed_page_limit(self):
        approved=validate_historical_source_contract(contract=self.contract(),decision_cutoff="2025-02-02T00:00:00+05:45")
        calls=[]
        def fetch(url):
            calls.append(url)
            return {"status_code":200,"final_url":url,"content_type":"text/csv","body":b"symbol,date,open,high,low,close,volume\nAAA,2025-01-02,10,12,9,11,100\n","has_more":False,"available_at":"2025-02-01T10:00:00+05:45"}
        out=capture_approved_historical_source(source_contract_report=approved,fetch_page=fetch,captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CAPTURED_PENDING_MANIFEST_VALIDATION")
        self.assertEqual(len(calls),1)
        self.assertFalse(out["backtest_admission_allowed"])
    def test_unapproved_contract_never_calls_transport(self):
        calls=[]
        out=capture_approved_historical_source(source_contract_report={"status":"CONTRACT_BLOCKED","capture_allowed":False},fetch_page=lambda url:calls.append(url),captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CAPTURE_BLOCKED")
        self.assertEqual(calls,[])


if __name__=="__main__": unittest.main()

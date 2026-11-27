import unittest
from app.historical_pilot_source_contract import validate_historical_source_contract
from app.historical_pilot_source_capture import capture_approved_historical_source
from app.historical_pilot_ohlcv_pipeline import ingest_accepted_historical_ohlcv_capture


class HistoricalOhlcvPipelineTests(unittest.TestCase):
    def setup_pipeline(self):
        contract={"source_id":"SRC","publisher_id":"PUB","dataset_kind":"official_eod_ohlcv","endpoint_url":"https://data.example.test/eod","allowed_hosts":["data.example.test"],"allowed_content_types":["text/csv"],"window_start":"2025-01-01T00:00:00+05:45","window_end":"2025-01-31T23:59:00+05:45","review_status":"approved","approved_by_human":True,"reviewer_id":"reviewer-1","reviewed_at":"2025-02-01T09:00:00+05:45","authority_evidence_ref":"DOC-1","licence_reviewed":True,"access_policy_reviewed":True,"authentication_mode":"public","page_parameter":"page","terminal_signal":"has_more_false","max_pages":10,"minimum_request_interval_seconds":1.0,"capture_id":"CAP-1"}
        approved=validate_historical_source_contract(contract=contract,decision_cutoff="2025-02-02T00:00:00+05:45")
        raw=b"symbol,date,open,high,low,close,volume\nAAA,2025-01-02,10,12,9,11,100\n"
        def fetch(url):
            return {"status_code":200,"final_url":url,"content_type":"text/csv","body":raw,"has_more":False,"available_at":"2025-02-01T10:00:00+05:45"}
        capture=capture_approved_historical_source(source_contract_report=approved,fetch_page=fetch,captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        return approved,capture
    def test_verified_capture_ingests_with_explicit_mapping(self):
        approved,capture=self.setup_pipeline()
        out=ingest_accepted_historical_ohlcv_capture(source_contract_report=approved,capture_result=capture,payloads=capture["payloads"],column_map={"symbol":"symbol","session_date":"date","open":"open","high":"high","low":"low","close":"close","volume":"volume"},decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"INGESTED",msg=repr(out.get("errors")))
        self.assertEqual(out["row_count"],1)
        self.assertFalse(out["backtest_admission_allowed"])
    def test_wrong_dataset_kind_fails_closed(self):
        approved,capture=self.setup_pipeline()
        approved["capture_spec"]["dataset_kind"]="official_floorsheet"
        out=ingest_accepted_historical_ohlcv_capture(source_contract_report=approved,capture_result=capture,payloads=capture["payloads"],column_map={"symbol":"symbol","session_date":"date","open":"open","high":"high","low":"low","close":"close","volume":"volume"},decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"INGESTION_BLOCKED")


if __name__=="__main__": unittest.main()

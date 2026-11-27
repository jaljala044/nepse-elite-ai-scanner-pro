import hashlib
import unittest
from app.historical_pilot_ingest import ingest_captured_ohlcv_csv

class CapturedOHLCVIngestTests(unittest.TestCase):
    def fixture(self):
        raw=b"ticker,date,o,h,l,c,qty\nAAA,2025-01-02,10,12,9,11,100\n"
        digest=hashlib.sha256(raw).hexdigest()
        manifest={"available_at":"2025-01-02T16:00:00+05:45","capture_id":"CAP-1","pages":[{"page_number":1,"payload_id":"p1"}]}
        report={"status":"CAPTURE_VALIDATED","source_id":"SRC-1","publisher_id":"PUB-1","verified_pages":[{"payload_id":"p1","raw_sha256":digest}]}
        mapping={"symbol":"ticker","session_date":"date","open":"o","high":"h","low":"l","close":"c","volume":"qty"}
        return raw,manifest,report,mapping
    def test_ingests_and_preserves_hash_provenance(self):
        raw,m,r,c=self.fixture()
        out=ingest_captured_ohlcv_csv(capture_report=r,manifest=m,payloads={"p1":raw},column_map=c,decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(out["status"],"INGESTED")
        self.assertEqual(out["rows"][0]["raw_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertFalse(out["backtest_admission_allowed"])
    def test_changed_bytes_block(self):
        raw,m,r,c=self.fixture()
        out=ingest_captured_ohlcv_csv(capture_report=r,manifest=m,payloads={"p1":raw+b"x"},column_map=c,decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")
    def test_missing_column_blocks(self):
        raw,m,r,c=self.fixture(); c["volume"]="missing"
        out=ingest_captured_ohlcv_csv(capture_report=r,manifest=m,payloads={"p1":raw},column_map=c,decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")
    def test_future_capture_blocks(self):
        raw,m,r,c=self.fixture(); m["available_at"]="2025-01-04T00:00:00+05:45"
        out=ingest_captured_ohlcv_csv(capture_report=r,manifest=m,payloads={"p1":raw},column_map=c,decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")

if __name__=="__main__": unittest.main()

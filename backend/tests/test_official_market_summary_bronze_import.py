from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from app.evidence_store import load_evidence_records
from import_official_market_summary_to_bronze import import_capture

class OfficialMarketSummaryBronzeImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name); self.capture = self.root / "capture"
        self.capture.mkdir(); self.storage = self.root / "raw"; self.db = self.root / "evidence.duckdb"
        self.payload = json.dumps([
            {"businessDate":"2026-11-25","totalTurnover":1000,"totalTradedShares":500,"totalTransactions":20,"tradedScrips":12},
            {"businessDate":"2026-11-26","totalTurnover":0,"totalTradedShares":0,"totalTransactions":0,"tradedScrips":0}
        ]).encode()
        self.report = {"source_id":"NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY",
            "source_url":"https://nepalstock.com.np/api/nots/market-summary-history",
            "retrieved_at_utc":"2026-11-26T15:00:00Z","http_status":200,
            "response_preserved":True,"response_bytes":len(self.payload),
            "response_sha256":hashlib.sha256(self.payload).hexdigest(),
            "selected_attempt_number":1,"response_headers":{"content-type":"application/json"}}
        self.write()
    def tearDown(self): self.tmp.cleanup()
    def write(self):
        (self.capture/"response-body.bin").write_bytes(self.payload)
        (self.capture/"capture-report.json").write_text(json.dumps(self.report))
    def run_import(self):
        return import_capture(self.capture, storage_root=self.storage, database_path=self.db)
    def test_import_preserves_raw_and_forces_provisional(self):
        result=self.run_import()
        rows=load_evidence_records(database_path=self.db,record_type="market_summary")
        self.assertEqual(result["normalized_records"],2); self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["session_date"],"2026-11-25")
        self.assertEqual(rows[0]["source_validation_status"],"review_required")
        self.assertEqual(rows[0]["finality_status"],"provisional")
        self.assertFalse(result["production_eligible"])
        self.assertEqual(Path(result["raw_object_path"]).read_bytes(),self.payload)
    def test_exact_replay_is_idempotent(self):
        first=self.run_import(); second=self.run_import()
        self.assertFalse(first["idempotent"]); self.assertTrue(second["idempotent"])
        self.assertEqual(len(load_evidence_records(database_path=self.db)),2)
    def test_rejects_non_official_host(self):
        self.report["source_url"]="https://example.invalid/api/nots/market-summary-history"; self.write()
        with self.assertRaisesRegex(ValueError,"not an approved official"): self.run_import()
    def test_rejects_hash_mismatch(self):
        self.report["response_sha256"]="0"*64; self.write()
        with self.assertRaisesRegex(ValueError,"SHA-256"): self.run_import()
    def test_rejects_non_200(self):
        self.report["http_status"]=503; self.write()
        with self.assertRaisesRegex(ValueError,"HTTP 200"): self.run_import()
    def test_rejects_naive_timestamp(self):
        self.report["retrieved_at_utc"]="2026-11-26T15:00:00"; self.write()
        with self.assertRaisesRegex(ValueError,"timezone-aware"): self.run_import()

if __name__ == "__main__": unittest.main()

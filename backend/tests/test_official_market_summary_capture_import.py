import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.evidence_store import load_evidence_records
from import_nepse_market_summary_capture import import_capture


class OfficialMarketSummaryImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.capture_dir = self.root / "capture"
        self.capture_dir.mkdir()
        self.db = self.root / "evidence.duckdb"
        self.storage = self.root / "raw"
        self.payload = json.dumps([
            {"businessDate":"2026-11-25","totalTurnover":1000000,
             "totalTradedShares":10000,"totalTransactions":500,"tradedScrips":100},
            {"businessDate":"2026-11-26","totalTurnover":2000000,
             "totalTradedShares":20000,"totalTransactions":600,"tradedScrips":110},
        ]).encode()
        (self.capture_dir / "response-body.bin").write_bytes(self.payload)
        report = {
            "source_id":"NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY",
            "source_url":"https://nepalstock.com.np/api/nots/market-summary-history",
            "retrieved_at_utc":"2026-11-26T12:00:00Z",
            "http_status":200,"response_preserved":True,"response_origin_verified":True,
            "response_sha256":hashlib.sha256(self.payload).hexdigest(),
            "response_bytes":len(self.payload),
        }
        (self.capture_dir / "capture-report.json").write_text(json.dumps(report), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_official_capture_imports_as_provisional_bronze_not_canonical(self):
        result = import_capture(self.capture_dir / "capture-report.json",
                                storage_root=self.storage, database_path=self.db)
        self.assertEqual(result["normalized_rows"], 2)
        self.assertTrue(result["row_conservation_passed"])
        self.assertFalse(result["production_eligible"])
        rows = load_evidence_records(database_path=self.db)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["record_type"] == "market_summary" for row in rows))
        self.assertTrue(all(row["source_validation_status"] == "review_required" for row in rows))
        self.assertTrue(all(row["finality_status"] == "provisional" for row in rows))
        self.assertEqual(load_evidence_records(database_path=self.db, include_provisional=False), [])

    def test_unverified_origin_is_rejected_before_import(self):
        report_path = self.capture_dir / "capture-report.json"
        report = json.loads(report_path.read_text())
        report["response_origin_verified"] = False
        report_path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "official origin"):
            import_capture(report_path, storage_root=self.storage, database_path=self.db)

    def test_payload_tampering_is_rejected(self):
        (self.capture_dir / "response-body.bin").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "digest or length"):
            import_capture(self.capture_dir / "capture-report.json",
                           storage_root=self.storage, database_path=self.db)


if __name__ == "__main__":
    unittest.main()

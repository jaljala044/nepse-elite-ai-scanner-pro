import hashlib
import shutil
import tempfile

import duckdb
import unittest
from pathlib import Path

from app.evidence_recovery import audit_evidence_store
from app.evidence_store import persist_evidence_batch
from app.raw_capture import build_capture_manifest


class EvidenceRecoveryAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "raw"
        self.db = self.base / "evidence.duckdb"
        self.payload = b"symbol,session_date,close\nNABIL,2026-11-25,500\n"
        self.manifest = build_capture_manifest(
            self.payload,
            source_id="secondary-example",
            source_url="https://example.invalid/ohlcv.csv",
            request_method="GET",
            request_metadata={"fixture": True},
            requested_at="2026-11-26T00:00:00Z",
            received_at="2026-11-26T00:00:02Z",
            claimed_session_date="2026-11-25",
            fetch_id="recovery-fetch-001",
            parser_version="ohlcv-csv-v1",
            rights_status="unknown",
        )
        self.records = [{
            "source_row_number": 2,
            "record_type": "ohlcv",
            "symbol": "NABIL",
            "session_date": "2026-11-25",
            "close": "500",
        }]
        persist_evidence_batch(
            self.payload, self.manifest, self.records,
            storage_root=self.root, database_path=self.db,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def audit(self):
        return audit_evidence_store(database_path=self.db, storage_root=self.root)

    def test_clean_reopen_audit_verifies_payload_manifest_and_record_lineage(self):
        report = self.audit()
        self.assertEqual(report["status"], "integrity_ok")
        self.assertEqual(report["raw_objects_checked"], 1)
        self.assertEqual(report["captures_checked"], 1)
        self.assertEqual(report["normalized_records_checked"], 1)
        self.assertEqual(report["issues"], [])
        self.assertFalse(report["production_eligible"])
        self.assertFalse(report["mutated_storage"])

    def test_payload_tampering_is_reported_without_repair_or_deletion(self):
        payload_path = next(self.root.rglob("payload.bin"))
        payload_path.write_bytes(b"tampered")
        report = self.audit()
        self.assertEqual(report["status"], "integrity_issues")
        self.assertIn(
            "raw_payload_hash_mismatch",
            {issue["code"] for issue in report["issues"]},
        )
        self.assertEqual(payload_path.read_bytes(), b"tampered")
        self.assertFalse(report["mutated_storage"])

    def test_catalog_payload_path_outside_storage_root_is_rejected(self):
        outside = self.base / "outside-payload.bin"
        outside.write_bytes(self.payload)
        con = duckdb.connect(str(self.db))
        try:
            con.execute("UPDATE raw_source_objects SET payload_path=?", [str(outside)])
        finally:
            con.close()

        report = self.audit()
        self.assertEqual(report["status"], "integrity_issues")
        self.assertIn(
            "raw_payload_path_outside_storage_root",
            {issue["code"] for issue in report["issues"]},
        )
        self.assertEqual(outside.read_bytes(), self.payload)
        self.assertFalse(report["mutated_storage"])

    def test_catalog_manifest_path_outside_storage_root_is_rejected(self):
        con = duckdb.connect(str(self.db), read_only=True)
        try:
            original_path = con.execute(
                "SELECT manifest_path FROM source_captures"
            ).fetchone()[0]
        finally:
            con.close()
        original = Path(original_path)
        outside = self.base / "outside-manifest.json"
        shutil.copy2(original, outside)
        con = duckdb.connect(str(self.db))
        try:
            con.execute("UPDATE source_captures SET manifest_path=?", [str(outside)])
        finally:
            con.close()

        report = self.audit()
        self.assertEqual(report["status"], "integrity_issues")
        self.assertIn(
            "capture_manifest_path_outside_storage_root",
            {issue["code"] for issue in report["issues"]},
        )
        self.assertTrue(outside.is_file())
        self.assertFalse(report["mutated_storage"])

    def test_unindexed_payload_is_reported_and_preserved(self):
        orphan = self.root / "secondary-example" / "2026-11-25" / ("f" * 64) / "payload.bin"
        orphan.parent.mkdir(parents=True)
        orphan.write_bytes(b"orphan evidence")
        report = self.audit()
        self.assertIn(str(orphan), report["orphan_raw_objects"])
        self.assertTrue(orphan.exists())
        self.assertFalse(report["mutated_storage"])

    def test_missing_database_fails_closed_without_creating_it(self):
        missing = self.base / "missing.duckdb"
        report = audit_evidence_store(database_path=missing, storage_root=self.root)
        self.assertEqual(report["status"], "unavailable")
        self.assertIn("database_missing", {issue["code"] for issue in report["issues"]})
        self.assertFalse(missing.exists())
        self.assertFalse(report["production_eligible"])

    def test_exact_replay_after_reopen_keeps_one_normalized_record(self):
        # The first persist call has closed its DuckDB connection. This second
        # call exercises a fresh connection against the existing on-disk DB.
        replay = persist_evidence_batch(
            self.payload, self.manifest, self.records,
            storage_root=self.root, database_path=self.db,
        )
        self.assertTrue(replay["idempotent"])
        report = self.audit()
        self.assertEqual(report["normalized_records_checked"], 1)
        self.assertEqual(report["status"], "integrity_ok")


if __name__ == "__main__":
    unittest.main()

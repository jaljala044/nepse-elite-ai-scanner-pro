import json
import tempfile
import unittest
from pathlib import Path

from app.evidence_backup import (
    BACKUP_MANIFEST,
    create_evidence_backup,
    restore_evidence_backup,
    verify_evidence_backup,
)
from app.evidence_recovery import audit_evidence_store
from app.evidence_store import load_evidence_records, persist_evidence_batch
from app.raw_capture import build_capture_manifest


class EvidenceBackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.raw = self.base / "live-raw"
        self.db = self.base / "live.duckdb"
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
            fetch_id="backup-fetch-001",
            parser_version="ohlcv-csv-v1",
            rights_status="unknown",
        )
        self.rows = [{
            "source_row_number": 2,
            "record_type": "ohlcv",
            "symbol": "NABIL",
            "session_date": "2026-11-25",
            "close": "500",
        }]
        persist_evidence_batch(
            self.payload, self.manifest, self.rows,
            storage_root=self.raw, database_path=self.db,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_backup_restore_rebinds_paths_and_preserves_evidence(self):
        backup = self.base / "backups" / "backup-001"
        result = create_evidence_backup(
            database_path=self.db, storage_root=self.raw,
            backup_destination=backup, backup_id="backup-001",
            writers_quiesced=True,
        )
        self.assertEqual(result["status"], "backup_created")
        self.assertEqual(verify_evidence_backup(backup)["status"], "verified")
        restored = self.base / "restores" / "restore-001"
        restored_result = restore_evidence_backup(
            backup_path=backup, restore_destination=restored,
        )
        self.assertEqual(restored_result["status"], "restore_verified")
        self.assertEqual(restored_result["restored_audit"]["status"], "integrity_ok")
        records = load_evidence_records(
            database_path=restored / "evidence.duckdb"
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["symbol"], "NABIL")
        self.assertEqual(records[0]["source_validation_status"], "review_required")
        self.assertEqual(
            audit_evidence_store(
                database_path=restored / "evidence.duckdb",
                storage_root=restored / "raw",
            )["status"],
            "integrity_ok",
        )
        self.assertTrue(self.db.exists())
        self.assertTrue(self.raw.exists())

    def test_backup_refuses_when_writers_not_quiesced(self):
        with self.assertRaisesRegex(ValueError, "writers_quiesced"):
            create_evidence_backup(
                database_path=self.db, storage_root=self.raw,
                backup_destination=self.base / "backup",
                backup_id="backup-002", writers_quiesced=False,
            )

    def test_backup_never_overwrites_existing_destination(self):
        destination = self.base / "backup"
        destination.mkdir()
        with self.assertRaises(FileExistsError):
            create_evidence_backup(
                database_path=self.db, storage_root=self.raw,
                backup_destination=destination,
                backup_id="backup-003", writers_quiesced=True,
            )

    def test_corrupted_backup_is_rejected_before_restore(self):
        backup = self.base / "backup"
        create_evidence_backup(
            database_path=self.db, storage_root=self.raw,
            backup_destination=backup, backup_id="backup-004",
            writers_quiesced=True,
        )
        payload = next((backup / "raw").rglob("payload.bin"))
        payload.write_bytes(b"tampered backup")
        self.assertEqual(verify_evidence_backup(backup)["status"], "integrity_issues")
        with self.assertRaisesRegex(ValueError, "verification failed"):
            restore_evidence_backup(
                backup_path=backup, restore_destination=self.base / "restore"
            )
        self.assertFalse((self.base / "restore").exists())

    def test_restore_refuses_to_overwrite_existing_destination(self):
        backup = self.base / "backup"
        create_evidence_backup(
            database_path=self.db, storage_root=self.raw,
            backup_destination=backup, backup_id="backup-005",
            writers_quiesced=True,
        )
        destination = self.base / "restore"
        destination.mkdir()
        with self.assertRaises(FileExistsError):
            restore_evidence_backup(
                backup_path=backup, restore_destination=destination
            )

    def test_backup_manifest_inventory_detects_extra_files(self):
        backup = self.base / "backup"
        create_evidence_backup(
            database_path=self.db, storage_root=self.raw,
            backup_destination=backup, backup_id="backup-006",
            writers_quiesced=True,
        )
        (backup / "unexpected.bin").write_bytes(b"untracked")
        report = verify_evidence_backup(backup)
        self.assertEqual(report["status"], "integrity_issues")
        self.assertIn("backup_file_inventory_mismatch", report["issues"])


if __name__ == "__main__":
    unittest.main()

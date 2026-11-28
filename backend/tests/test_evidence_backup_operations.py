import json
import multiprocessing
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.evidence_backup import create_evidence_backup, restore_evidence_backup
from app.evidence_backup_operations import (
    audit_backup_retention,
    audit_restore_drill_log,
    record_restore_drill,
)
from app.evidence_store import persist_evidence_batch
from app.raw_capture import build_capture_manifest


def _append_restore_drill_worker(log_path, drill_id):
    record_restore_drill(
        log_path=log_path,
        drill_id=drill_id,
        backup_id="backup-concurrent",
        restore_result={
            "status": "restore_verified",
            "restored_audit": {"status": "integrity_ok"},
        },
    )


class EvidenceBackupOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.raw = self.base / "raw"
        self.db = self.base / "evidence.duckdb"
        payload = b"symbol,session_date,close\nNABIL,2026-11-25,500\n"
        manifest = build_capture_manifest(
            payload, source_id="secondary-example",
            source_url="https://example.invalid/ohlcv.csv",
            request_method="GET", request_metadata={"fixture": True},
            requested_at="2026-11-26T00:00:00Z",
            received_at="2026-11-26T00:00:02Z",
            claimed_session_date="2026-11-25", fetch_id="ops-fetch-001",
            parser_version="ohlcv-csv-v1", rights_status="unknown",
        )
        rows = [{
            "source_row_number": 2, "record_type": "ohlcv",
            "symbol": "NABIL", "session_date": "2026-11-25", "close": "500",
        }]
        persist_evidence_batch(payload, manifest, rows, storage_root=self.raw, database_path=self.db)
        self.backup_root = self.base / "backups"
        self.backup_root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def make_backup(self, backup_id, created_at):
        destination = self.backup_root / backup_id
        create_evidence_backup(
            database_path=self.db, storage_root=self.raw,
            backup_destination=destination, backup_id=backup_id,
            writers_quiesced=True,
        )
        manifest_path = destination / "backup-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["created_at_utc"] = created_at.isoformat().replace("+00:00", "Z")
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        return destination

    def make_restore_result(self, backup_id="backup-1"):
        backup = self.backup_root / backup_id
        restored = self.base / "restore" / backup_id
        return restore_evidence_backup(backup_path=backup, restore_destination=restored)

    def test_fresh_backup_without_drill_is_not_healthy_by_default(self):
        now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
        self.make_backup("backup-1", now - timedelta(hours=1))
        report = audit_backup_retention(backup_root=self.backup_root, now_utc=now)
        self.assertEqual(report["status"], "attention_required")
        self.assertIn("restore_drill_log_not_configured", report["issues"])
        self.assertEqual(report["valid_backups"][0]["backup_id"], "backup-1")
        self.assertFalse(report["deletion_performed"])
        self.assertFalse(report["production_eligible"])

    def test_stale_latest_backup_is_flagged(self):
        now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
        self.make_backup("backup-old", now - timedelta(hours=30))
        report = audit_backup_retention(
            backup_root=self.backup_root, now_utc=now,
            require_restore_drill=False, max_backup_age_hours=26,
        )
        self.assertEqual(report["status"], "attention_required")
        self.assertIn("latest_valid_backup_stale_or_missing", report["issues"])
        self.assertEqual(report["stale_backup_ids"], ["backup-old"])

    def test_retention_candidates_are_advisory_and_keep_newest_n(self):
        now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
        for i in range(3):
            self.make_backup(f"backup-{i}", now - timedelta(hours=i))
        report = audit_backup_retention(
            backup_root=self.backup_root, now_utc=now,
            require_restore_drill=False, retain_last=2,
        )
        self.assertEqual(report["retention_review_candidates"], ["backup-2"])
        self.assertFalse(report["deletion_performed"])
        self.assertEqual(report["status"], "healthy")

    def test_restore_drill_log_is_hash_chained_and_fresh(self):
        now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
        self.make_backup("backup-1", now - timedelta(hours=1))
        restore_result = self.make_restore_result()
        log = self.base / "ops" / "restore-drills.jsonl"
        recorded = record_restore_drill(
            log_path=log, drill_id="drill-001", backup_id="backup-1",
            restore_result=restore_result, recorded_at_utc=now - timedelta(days=2),
        )
        self.assertEqual(recorded["status"], "restore_drill_recorded")
        audit = audit_restore_drill_log(log)
        self.assertEqual(audit["status"], "verified")
        self.assertEqual(audit["events_checked"], 1)
        report = audit_backup_retention(
            backup_root=self.backup_root, now_utc=now,
            restore_drill_log=log, max_restore_drill_age_days=90,
        )
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["restore_drill"]["age_days"], 2.0)

    def test_restore_drill_rejects_unverified_restore_and_duplicate_id(self):
        log = self.base / "restore-drills.jsonl"
        with self.assertRaisesRegex(ValueError, "only a successful isolated restore"):
            record_restore_drill(
                log_path=log, drill_id="bad", backup_id="backup-1",
                restore_result={"status": "restore_failed", "restored_audit": {"status": "integrity_issues"}},
            )
        now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
        self.make_backup("backup-1", now - timedelta(hours=1))
        result = self.make_restore_result()
        record_restore_drill(
            log_path=log, drill_id="same", backup_id="backup-1",
            restore_result=result, recorded_at_utc=now,
        )
        with self.assertRaisesRegex(ValueError, "already exists"):
            record_restore_drill(
                log_path=log, drill_id="same", backup_id="backup-1",
                restore_result=result, recorded_at_utc=now,
            )

    def test_concurrent_restore_drill_appends_preserve_one_hash_chain(self):
        log = self.base / "ops" / "concurrent-restore-drills.jsonl"
        processes = [
            multiprocessing.Process(
                target=_append_restore_drill_worker,
                args=(str(log), f"parallel-{index}"),
            )
            for index in range(8)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=20)
        for process in processes:
            self.assertFalse(process.is_alive(), "append worker timed out")
            self.assertEqual(process.exitcode, 0)

        audit = audit_restore_drill_log(log)
        self.assertEqual(audit["status"], "verified")
        self.assertEqual(audit["events_checked"], 8)

    def test_restore_drill_writer_rejects_symlink_log_path(self):
        target = self.base / "target.jsonl"
        target.write_text("")
        link = self.base / "restore-drills.jsonl"
        link.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            record_restore_drill(
                log_path=link,
                drill_id="symlink-attempt",
                backup_id="backup-1",
                restore_result={
                    "status": "restore_verified",
                    "restored_audit": {"status": "integrity_ok"},
                },
            )
        self.assertEqual(target.read_text(), "")

    def test_tampered_restore_drill_log_fails_closed(self):
        log = self.base / "restore-drills.jsonl"
        log.write_text(json.dumps({
            "schema_version": 1, "drill_id": "forged",
            "previous_event_sha256": "0" * 64,
            "event_sha256": "f" * 64,
        }) + "\n")
        report = audit_restore_drill_log(log)
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(report["issues"])


if __name__ == "__main__":
    unittest.main()

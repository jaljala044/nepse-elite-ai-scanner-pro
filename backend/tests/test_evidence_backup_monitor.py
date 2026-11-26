import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.evidence_backup import BACKUP_MANIFEST
from app.evidence_backup_monitor import inspect_backup_retention


class EvidenceBackupMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "backups"
        self.root.mkdir()
        self.now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def add_backup(self, name, created_at, *, corrupt=False, malformed=False):
        folder = self.root / name
        folder.mkdir()
        payload = folder / "evidence.duckdb"
        payload.write_bytes(b"synthetic database bytes")
        raw = folder / "raw"
        raw.mkdir()
        (raw / "payload.bin").write_bytes(b"synthetic raw bytes")
        files = {}
        for path in (payload, raw / "payload.bin"):
            data = path.read_bytes()
            files[path.relative_to(folder).as_posix()] = {
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        if corrupt:
            (raw / "payload.bin").write_bytes(b"tampered")
        manifest = {
            "schema_version": 1,
            "backup_id": name,
            "created_at_utc": created_at,
            "files": files,
            "production_eligible": False,
        }
        if malformed:
            manifest["created_at_utc"] = "not-a-timestamp"
        (folder / BACKUP_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
        return folder

    def test_fresh_verified_backup_is_ready(self):
        self.add_backup("b1", "2026-11-26T10:00:00Z")
        report = inspect_backup_retention(backup_root=self.root, now=self.now)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["valid_backup_count"], 1)
        self.assertFalse(report["scheduled_backup_overdue"])

    def test_no_backups_is_critical_and_schedule_is_overdue(self):
        report = inspect_backup_retention(backup_root=self.root, now=self.now)
        self.assertEqual(report["status"], "critical")
        self.assertTrue(report["scheduled_backup_overdue"])
        self.assertTrue(report["operator_action_required"])

    def test_stale_latest_valid_backup_is_critical(self):
        self.add_backup("old", "2026-11-24T00:00:00Z")
        report = inspect_backup_retention(backup_root=self.root, now=self.now)
        self.assertEqual(report["status"], "critical")
        self.assertTrue(report["stale_latest_valid_backup"])

    def test_corrupt_backup_is_not_counted_as_valid(self):
        self.add_backup("bad", "2026-11-26T10:00:00Z", corrupt=True)
        report = inspect_backup_retention(backup_root=self.root, now=self.now)
        self.assertEqual(report["status"], "critical")
        self.assertEqual(report["valid_backup_count"], 0)
        self.assertEqual(report["invalid_backup_count"], 1)

    def test_malformed_timestamp_is_quarantined_in_report(self):
        self.add_backup("bad-time", "2026-11-26T10:00:00Z", malformed=True)
        report = inspect_backup_retention(backup_root=self.root, now=self.now)
        self.assertEqual(report["invalid_backup_count"], 1)
        self.assertEqual(report["invalid_backups"][0]["reason"], "backup_manifest_invalid")

    def test_retention_candidates_are_non_destructive(self):
        for i in range(4):
            stamp = (self.now - timedelta(hours=i)).isoformat().replace("+00:00", "Z")
            self.add_backup(f"b{i}", stamp)
        report = inspect_backup_retention(
            backup_root=self.root, now=self.now, keep_last=2
        )
        self.assertEqual(len(report["retention_candidates"]), 2)
        self.assertFalse(report["retention_policy"]["automatic_deletion"])
        self.assertTrue(all(Path(item["path"]).exists() for item in report["retention_candidates"]))

    def test_future_timestamp_is_rejected(self):
        future = (self.now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        self.add_backup("future", future)
        report = inspect_backup_retention(backup_root=self.root, now=self.now)
        self.assertEqual(report["valid_backup_count"], 0)
        self.assertEqual(report["invalid_backup_count"], 1)

    def test_naive_clock_and_invalid_policy_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            inspect_backup_retention(
                backup_root=self.root, now=datetime(2026, 11, 26, 12)
            )
        with self.assertRaisesRegex(ValueError, "keep_last"):
            inspect_backup_retention(
                backup_root=self.root, now=self.now, keep_last=0
            )


if __name__ == "__main__":
    unittest.main()

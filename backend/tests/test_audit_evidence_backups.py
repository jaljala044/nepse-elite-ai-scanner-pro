import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.audit_evidence_backups import audit


class BackupReadinessSymlinkTests(unittest.TestCase):
    def test_symlink_backup_directory_is_counted_as_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "backup-root"
            root.mkdir()
            target = base / "outside"
            target.mkdir()
            (target / "backup-manifest.json").write_text("{}", encoding="utf-8")
            (root / "linked-backup").symlink_to(target, target_is_directory=True)

            result = audit(root, max_age_hours=30, minimum_verified=1)

            self.assertEqual(result["invalid_backup_count"], 1)
            self.assertFalse(result["integrity_ok"])
            self.assertEqual(result["invalid_backups"][0]["reason"], "backup_entry_is_symlink")
            self.assertEqual(result["status"], "not_ready")

    def test_symlink_manifest_is_counted_as_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "backup-1"
            backup.mkdir()
            outside = root / "outside-manifest.json"
            outside.write_text("{}", encoding="utf-8")
            (backup / "backup-manifest.json").symlink_to(outside)

            result = audit(root, max_age_hours=30, minimum_verified=1)

            self.assertEqual(result["invalid_backup_count"], 1)
            self.assertEqual(result["invalid_backups"][0]["reason"], "backup_manifest_is_symlink")
            self.assertEqual(result["status"], "not_ready")

    def test_nested_symlink_is_counted_as_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "backup-1"
            backup.mkdir()
            (backup / "backup-manifest.json").write_text("{}", encoding="utf-8")
            outside = root / "payload.bin"
            outside.write_bytes(b"payload")
            (backup / "payload.bin").symlink_to(outside)

            result = audit(root, max_age_hours=30, minimum_verified=1)

            self.assertEqual(result["invalid_backup_count"], 1)
            self.assertEqual(result["invalid_backups"][0]["reason"], "backup_contains_symlink")
            self.assertEqual(result["status"], "not_ready")


if __name__ == "__main__":
    unittest.main()

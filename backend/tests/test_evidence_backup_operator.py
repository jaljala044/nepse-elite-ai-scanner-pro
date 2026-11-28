from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "create_evidence_backup.py"
SPEC = importlib.util.spec_from_file_location("create_evidence_backup_cli", SCRIPT)
CLI = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(CLI)

from app.evidence_backup import _validate_backup_source_destination

_require_separate_filesystem = CLI._require_separate_filesystem


class EvidenceBackupOperatorPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "raw"
        self.destination = self.root / "backup-mount"
        self.source.mkdir()
        self.destination.mkdir()
        self.database = self.root / "evidence.duckdb"
        self.database.write_bytes(b"synthetic")

    def tearDown(self):
        self.temp.cleanup()

    def test_requires_real_mount_point(self):
        with patch.object(CLI.os.path, "ismount", return_value=False):
            with self.assertRaisesRegex(ValueError, "not a mounted filesystem"):
                CLI.validate_backup_paths(str(self.database), str(self.source), str(self.destination))

    def test_accepts_existing_isolated_mount_point(self):
        with patch.object(CLI.os.path, "ismount", return_value=True), patch.object(
            CLI, "_require_separate_filesystem"
        ):
            database, source, destination = CLI.validate_backup_paths(
                str(self.database), str(self.source), str(self.destination)
            )
        self.assertEqual(database, self.database.resolve())
        self.assertEqual(source, self.source.resolve())
        self.assertEqual(destination, self.destination.resolve())

    def test_rejects_destination_nested_in_raw_source(self):
        nested = self.source / "backups"
        nested.mkdir()
        with patch.object(CLI.os.path, "ismount", return_value=True):
            with self.assertRaisesRegex(ValueError, "must not overlap"):
                CLI.validate_backup_paths(str(self.database), str(self.source), str(nested))

    def test_rejects_raw_source_nested_in_destination(self):
        nested_source = self.destination / "raw"
        nested_source.mkdir()
        with patch.object(CLI.os.path, "ismount", return_value=True):
            with self.assertRaisesRegex(ValueError, "must not overlap"):
                CLI.validate_backup_paths(str(self.database), str(nested_source), str(self.destination))

    def test_rejects_database_inside_backup_destination(self):
        nested_db = self.destination / "evidence.duckdb"
        nested_db.write_bytes(b"synthetic")
        with patch.object(CLI.os.path, "ismount", return_value=True):
            with self.assertRaisesRegex(ValueError, "database source"):
                CLI.validate_backup_paths(str(nested_db), str(self.source), str(self.destination))

    def test_same_filesystem_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "separate filesystem"):
            _require_separate_filesystem(1, 1, 1)

    def test_destination_matching_database_filesystem_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "separate filesystem"):
            _require_separate_filesystem(1, 2, 1)

    def test_destination_matching_raw_filesystem_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "separate filesystem"):
            _require_separate_filesystem(1, 2, 2)

    def test_distinct_filesystem_is_accepted(self):
        self.assertIsNone(_require_separate_filesystem(1, 2, 3))

    def test_validator_rejects_same_filesystem_even_when_mountpoint(self):
        with patch.object(CLI.os.path, "ismount", return_value=True):
            with self.assertRaisesRegex(ValueError, "separate filesystem"):
                CLI.validate_backup_paths(str(self.database), str(self.source), str(self.destination))

    def test_core_backup_rejects_recursive_destination(self):
        nested = self.source / "backup-output"
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            _validate_backup_source_destination(self.database, self.source, nested)

    def test_core_backup_rejects_database_inside_destination(self):
        nested_db = self.destination / "evidence.duckdb"
        with self.assertRaisesRegex(ValueError, "source database"):
            _validate_backup_source_destination(nested_db, self.source, self.destination)


if __name__ == "__main__":
    unittest.main()

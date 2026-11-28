import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from create_evidence_backup import validate_backup_destination, _require_separate_filesystem

class BackupDestinationGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / 'evidence.duckdb'
        self.db.write_bytes(b'db')
        self.raw = self.root / 'raw'
        self.dest = self.root / 'backup'
        self.raw.mkdir()
        self.dest.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_filesystem_destination_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'separate_filesystem'):
            validate_backup_destination(self.db, self.raw, self.dest)

    def test_distinct_filesystem_is_reported_without_claiming_off_host(self):
        result = _require_separate_filesystem(1, 1, 2)
        self.assertEqual(result["filesystem_separation"], "verified_distinct_device")
        self.assertEqual(result["off_host_status"], "not_verified_operator_confirmation_required")

    def test_destination_matching_database_device_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "separate_filesystem"):
            _require_separate_filesystem(1, 2, 1)

    def test_destination_matching_raw_store_device_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "separate_filesystem"):
            _require_separate_filesystem(1, 2, 2)


if __name__ == '__main__':
    unittest.main()
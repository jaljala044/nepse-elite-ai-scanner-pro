import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from create_evidence_backup import validate_backup_destination

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
        real_stat = os.stat
        def fake_stat(path, *args, **kwargs):
            result = real_stat(path, *args, **kwargs)
            if Path(path).resolve() == self.dest.resolve():
                return SimpleNamespace(st_dev=result.st_dev + 1)
            return result
        with patch('create_evidence_backup.os.stat', side_effect=fake_stat):
            result = validate_backup_destination(self.db, self.raw, self.dest)
        self.assertEqual(result['filesystem_separation'], 'verified_distinct_device')
        self.assertEqual(result['off_host_status'], 'not_verified_operator_confirmation_required')

if __name__ == '__main__':
    unittest.main()
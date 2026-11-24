import hashlib
import tempfile
import unittest
from pathlib import Path

from acquire_floorsheet_archive import (
    dated_csv,
    git_blob_sha1,
    verify_local_file,
)


class FloorsheetArchiveAcquisitionTests(unittest.TestCase):
    def test_extracts_valid_date_from_filename(self):
        self.assertEqual(
            dated_csv("floorsheet/floorsheet_2026-11-24.csv"), "2026-11-24"
        )

    def test_rejects_invalid_calendar_date(self):
        self.assertIsNone(dated_csv("floorsheet_2026-02-30.csv"))

    def test_ignores_non_csv_and_undated_names(self):
        self.assertIsNone(dated_csv("floorsheet/latest.csv"))
        self.assertIsNone(dated_csv("floorsheet_2026-11-24.json"))

    def test_git_blob_sha_uses_git_object_header(self):
        payload = b"abc"
        expected = hashlib.sha1(b"blob 3\0abc").hexdigest()
        self.assertEqual(git_blob_sha1(payload), expected)

    def test_existing_file_verifies_against_size_and_git_blob(self):
        payload = b"contract_no,quantity\n1,100\n"
        row = {
            "size_bytes": len(payload),
            "git_blob_sha1": git_blob_sha1(payload),
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv"
            path.write_bytes(payload)
            result = verify_local_file(path, row)
        self.assertEqual(result["downloaded_bytes"], len(payload))
        self.assertEqual(result["verification"], "size_and_git_blob_sha1_pass")
        self.assertEqual(result["local_sha256"], hashlib.sha256(payload).hexdigest())

    def test_existing_file_rejects_git_blob_mismatch(self):
        payload = b"wrong bytes"
        row = {"size_bytes": len(payload), "git_blob_sha1": "0" * 40}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv"
            path.write_bytes(payload)
            with self.assertRaises(ValueError):
                verify_local_file(path, row)


if __name__ == "__main__":
    unittest.main()

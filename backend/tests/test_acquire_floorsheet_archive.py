import hashlib
import unittest

from backend.acquire_floorsheet_archive import dated_csv, git_blob_sha1


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


if __name__ == "__main__":
    unittest.main()

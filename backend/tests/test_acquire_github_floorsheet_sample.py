import unittest

from acquire_github_floorsheet_sample import select_sample


class GitHubFloorsheetSampleTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"date": "2026-08-26", "path": "floorsheet/floorsheet_2026-08-26.csv", "size_bytes": 3588067, "git_blob_sha1": "a" * 40},
            {"date": "2026-08-25", "path": "floorsheet/floorsheet_2026-08-25.csv", "size_bytes": 3000000, "git_blob_sha1": "b" * 40},
        ]

    def test_selects_one_pinned_date(self):
        selected = select_sample(self.rows, "2026-08-26", 5000000)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["path"], "floorsheet/floorsheet_2026-08-26.csv")

    def test_rejects_missing_or_duplicate_date_files(self):
        with self.assertRaisesRegex(ValueError, "found 0"):
            select_sample(self.rows, "2026-08-27", 5000000)
        with self.assertRaisesRegex(ValueError, "found 2"):
            select_sample(self.rows + [dict(self.rows[0], path="floorsheet/another-2026-08-26.csv")], "2026-08-26", 5000000)

    def test_enforces_byte_ceiling_and_git_blob_hash(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            select_sample(self.rows, "2026-08-26", 1000)
        with self.assertRaisesRegex(ValueError, "no Git blob"):
            select_sample([{"date": "2026-08-26", "size_bytes": 10}], "2026-08-26", 100)


if __name__ == "__main__":
    unittest.main()

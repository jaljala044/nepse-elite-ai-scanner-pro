import unittest

from acquire_hf_floorsheet_sample import select_sample


class HuggingFaceFloorsheetSampleTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"date": "2026-08-26", "path": "floorsheet/2026-08-26.csv", "size_bytes": 1024, "lfs_sha256": "a" * 64},
            {"date": "2026-08-25", "path": "floorsheet/2026-08-25.csv", "size_bytes": 2048, "lfs_sha256": "b" * 64},
        ]

    def test_selects_exactly_one_date(self):
        selected = select_sample(self.rows, "2026-08-26", 2048)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["path"], "floorsheet/2026-08-26.csv")

    def test_refuses_missing_date(self):
        with self.assertRaisesRegex(ValueError, "found 0"):
            select_sample(self.rows, "2026-08-27", 2048)

    def test_refuses_multiple_files_for_same_date(self):
        rows = self.rows + [{"date": "2026-08-26", "path": "floorsheet/2026-08-26.csv.gz", "size_bytes": 10, "lfs_sha256": "c" * 64}]
        with self.assertRaisesRegex(ValueError, "found 2"):
            select_sample(rows, "2026-08-26", 2048)

    def test_enforces_byte_ceiling(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            select_sample(self.rows, "2026-08-26", 100)

    def test_requires_hub_sha256(self):
        rows = [{"date": "2026-08-26", "path": "floorsheet/2026-08-26.csv", "size_bytes": 10}]
        with self.assertRaisesRegex(ValueError, "no Hub LFS SHA-256"):
            select_sample(rows, "2026-08-26", 100)

    def test_rejects_invalid_date_and_zero_ceiling(self):
        with self.assertRaisesRegex(ValueError, "invalid sample date"):
            select_sample(self.rows, "2026-02-30", 100)
        with self.assertRaisesRegex(ValueError, "must be positive"):
            select_sample(self.rows, "2026-08-26", 0)


if __name__ == "__main__":
    unittest.main()

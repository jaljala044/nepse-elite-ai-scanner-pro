import tempfile
import unittest
from pathlib import Path

from acquire_github_floorsheet_window import load_dates, select_window


class GitHubFloorsheetWindowTests(unittest.TestCase):
    def setUp(self):
        self.dates = ["2026-08-25", "2026-08-26"]
        self.rows = [
            {"date": "2026-08-25", "path": "floorsheet/2026-08-25.csv", "size_bytes": 100, "git_blob_sha1": "a" * 40},
            {"date": "2026-08-26", "path": "floorsheet/2026-08-26.csv", "size_bytes": 200, "git_blob_sha1": "b" * 40},
        ]

    def test_selects_exact_date_window(self):
        selected = select_window(self.rows, self.dates, 500)
        self.assertEqual([x["date"] for x in selected], self.dates)

    def test_rejects_missing_date_and_duplicate_files(self):
        with self.assertRaisesRegex(ValueError, "missing source files"):
            select_window(self.rows[:1], self.dates, 500)
        with self.assertRaisesRegex(ValueError, "multiple source files"):
            select_window(self.rows + [dict(self.rows[0], path="floorsheet/alt-2026-08-25.csv")], self.dates, 500)

    def test_enforces_total_byte_ceiling_and_blob_hash(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            select_window(self.rows, self.dates, 250)
        bad = [dict(x) for x in self.rows]
        bad[0].pop("git_blob_sha1")
        with self.assertRaisesRegex(ValueError, "no Git blob"):
            select_window(bad, self.dates, 500)

    def test_loads_and_validates_date_list(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dates.csv"
            path.write_text(
                "date,index_status\\n2026-08-25,valid\\n2026-08-26,valid\\n",
                encoding="utf-8",
            )
            self.assertEqual(load_dates(path), self.dates)
            path.write_text("date\\n2026-08-25\\n2026-08-25\\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate dates"):
                load_dates(path)


if __name__ == "__main__":
    unittest.main()

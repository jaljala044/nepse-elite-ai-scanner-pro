import csv
import tempfile
import unittest
from pathlib import Path

from scripts.extract_repeated_adjacent_ohlcv import extract


class RepeatedAdjacentTests(unittest.TestCase):
    def test_only_identical_consecutive_ohlcv_rows_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "ABC_OHLCV.csv"
            file.write_text(
                "Date,Open,High,Low,Close,Volume\n"
                "2026-01-01,10,11,9,10,100\n"
                "2026-01-02,10,11,9,10,100\n"
                "2026-01-03,10,12,9,11,150\n",
                encoding="utf-8",
            )
            rows = extract("example/repo", "a" * 40, root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["previous_date"], "2026-01-01")
            self.assertEqual(rows[0]["current_date"], "2026-01-02")
            self.assertEqual(rows[0]["classification"],
                             "calendar_status_unverified_review_flag")


if __name__ == "__main__":
    unittest.main()

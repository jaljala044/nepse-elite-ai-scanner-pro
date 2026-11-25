import tempfile
import unittest
from pathlib import Path

from scripts.extract_repeated_adjacent_ohlcv import extract


class RepeatedAdjacentTests(unittest.TestCase):
    def _write(self, root: Path, rows: str) -> Path:
        file = root / "ABC_OHLCV.csv"
        file.write_text("Date,Open,High,Low,Close,Volume\n" + rows, encoding="utf-8")
        return file

    def test_only_identical_consecutive_complete_rows_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "2026-01-01,10,11,9,10,100\n"
                "2026-01-02,10,11,9,10,100\n"
                "2026-01-03,10,12,9,11,150\n",
            )
            rows = extract("example/repo", "a" * 40, root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["previous_date"], "2026-01-01")
            self.assertEqual(rows[0]["current_date"], "2026-01-02")
            self.assertEqual(rows[0]["classification"],
                             "calendar_status_unverified_review_flag")

    def test_incomplete_rows_are_not_repeated_signatures_and_break_adjacency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "2026-01-01,,,,,\n"
                "2026-01-02,,,,,\n"
                "2026-01-03,10,11,9,10,100\n"
                "2026-01-04,10,,9,10,100\n"
                "2026-01-05,10,11,9,10,100\n",
            )
            rows = extract("example/repo", "b" * 40, root)
            self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()

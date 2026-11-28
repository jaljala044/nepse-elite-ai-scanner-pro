import csv
import tempfile
import unittest
from pathlib import Path
from scripts.build_equity_coverage_ledger import inspect


class EquityCoverageLedgerTests(unittest.TestCase):
    def test_missing_file_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = inspect("NABIL", Path(tmp))
        self.assertEqual(row["status"], "MISSING_FILE")

    def test_duplicate_and_invalid_bars_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "NABIL_OHLCV.csv"
            with path.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["Date","Open","High","Low","Close","Volume"])
                w.writeheader()
                w.writerow(dict(Date="2025-01-01",Open="100",High="105",Low="95",Close="102",Volume="100"))
                w.writerow(dict(Date="2025-01-01",Open="100",High="90",Low="95",Close="102",Volume="100"))
            row = inspect("NABIL", root)
        self.assertEqual(row["duplicates"], 1)
        self.assertEqual(row["invalid_ohlcv"], 1)
        self.assertEqual(row["status"], "REVIEW_REQUIRED")

    def test_valid_file_is_coverage_only_not_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (root / "NABIL_OHLCV.csv").open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["Date","Open","High","Low","Close","Volume"])
                w.writeheader()
                w.writerow(dict(Date="2025-01-01",Open="100",High="105",Low="95",Close="102",Volume="100"))
            row = inspect("NABIL", root)
        self.assertEqual(row["status"], "OBSERVED_COVERAGE_ONLY")
        self.assertEqual(row["unique_sessions"], 1)


if __name__ == "__main__":
    unittest.main()

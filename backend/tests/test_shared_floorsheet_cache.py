import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import normalize_floorsheet as nf
from nepse_shared_validation import ValidationRegistry


class SharedFloorsheetCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.input = self.root / "floorsheet_2024-01-02.csv"
        self.registry = ValidationRegistry(self.root / "shared" / "registry.sqlite3")
        self.silver = self.root / "silver"
        self.quarantine = self.root / "quarantine"
        self.write_rows([self.row()])

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def row(contract="20240102000001", amount="5005"):
        return {
            "contract_no": contract, "calculation_date": "2024-01-02",
            "time": "", "stock_symbol": "NABIL", "sector": "Commercial Banks",
            "buyer": "58", "seller": "34", "quantity": "10",
            "rate": "500.5", "amount": amount, "id": contract,
        }

    def write_rows(self, rows):
        with self.input.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.row().keys()))
            writer.writeheader()
            writer.writerows(rows)

    def run_normalizer(self):
        with patch.object(nf, "ROOT", self.root), patch.object(nf, "SILVER", self.silver), patch.object(nf, "QUARANTINE", self.quarantine):
            return nf.normalize_floorsheet_csv(
                self.input, source="shared-cache-test", registry=self.registry
            )

    def test_identical_file_reuses_parsed_validation_rows(self):
        first = self.run_normalizer()
        self.assertFalse(first["validation_cache_hit"])
        with patch.object(nf, "_canonical_row", side_effect=AssertionError("must reuse cached parse")):
            second = self.run_normalizer()
        self.assertTrue(second["validation_cache_hit"])
        self.assertEqual(second["unique_rows_accepted"], 1)

    def test_changed_file_is_reparsed(self):
        first = self.run_normalizer()
        self.assertFalse(first["validation_cache_hit"])
        self.write_rows([
            self.row(),
            self.row(contract="20240102000002", amount="5005"),
        ])
        second = self.run_normalizer()
        self.assertFalse(second["validation_cache_hit"])
        self.assertEqual(second["unique_rows_accepted"], 2)

if __name__ == "__main__":
    unittest.main()

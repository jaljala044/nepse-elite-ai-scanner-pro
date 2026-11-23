import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.normalize_floorsheet as nf

class NormalizeFloorsheetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.input_dir = self.root / "incoming"
        self.input_dir.mkdir()
        self.silver = self.root / "data" / "silver" / "floorsheet"
        self.quarantine = self.root / "data" / "quarantine"

    def tearDown(self):
        self.tmp.cleanup()

    def write_csv(self, rows):
        path = self.input_dir / "floorsheet_2024-01-02.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "contract_no", "calculation_date", "time", "stock_symbol",
                "sector", "buyer", "seller", "quantity", "rate", "amount", "id"
            ])
            writer.writeheader()
            writer.writerows(rows)
        return path

    def row(self, **kwargs):
        base = {
            "contract_no": "20240102000001", "calculation_date": "2024-01-02",
            "time": "", "stock_symbol": "NABIL", "sector": "Commercial Banks",
            "buyer": "58", "seller": "34", "quantity": "10",
            "rate": "500.5", "amount": "5005", "id": "1",
        }
        base.update(kwargs)
        return base

    def run_import(self, path, **kwargs):
        with patch.object(nf, "ROOT", self.root), patch.object(nf, "SILVER", self.silver), patch.object(nf, "QUARANTINE", self.quarantine):
            return nf.normalize_floorsheet_csv(path, source="unit_test", **kwargs)

    def test_normalizes_trade_and_preserves_broker_codes(self):
        path = self.write_csv([self.row()])
        result = self.run_import(path)
        self.assertEqual(result["unique_rows_accepted"], 1)
        output = self.silver / "date=2024-01-02" / "floorsheet.csv"
        with output.open(encoding="utf-8") as f:
            imported = list(csv.DictReader(f))
        self.assertEqual(imported[0]["buyer_broker_code"], "58")
        self.assertEqual(imported[0]["seller_broker_code"], "34")
        self.assertEqual(imported[0]["symbol"], "NABIL")

    def test_identical_duplicate_contract_is_idempotently_deduplicated(self):
        path = self.write_csv([self.row(), self.row(id="2")])
        result = self.run_import(path)
        self.assertEqual(result["unique_rows_accepted"], 1)
        self.assertEqual(result["rows_rejected"], 0)

    def test_bad_amount_is_quarantined(self):
        path = self.write_csv([self.row(amount="9999")])
        result = self.run_import(path)
        self.assertEqual(result["rows_rejected"], 1)
        self.assertIsNotNone(result["quarantine_path"])

    def test_reject_ratio_gate_prevents_silver_write(self):
        path = self.write_csv([self.row(amount="9999")])
        with self.assertRaises(ValueError):
            self.run_import(path, max_reject_ratio=0.0)
        self.assertFalse(self.silver.exists())

if __name__ == "__main__":
    unittest.main()

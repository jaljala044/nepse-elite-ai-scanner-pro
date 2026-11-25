import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_floorsheet_duplicate_contract_ledger import duplicate_ledger, write_csv


class DuplicateContractLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.left = self.root / "left.csv"
        self.right = self.root / "right.csv"
        self.left.write_text(
            "date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
            "2026-11-24,1,C1,NABIL,11,22,2,100,200\n"
            "2026-11-24,1,C1,NABIL,11,22,2,100,200\n"
            "2026-11-24,3,C2,NABIL,11,22,1,100,100\n",
            encoding="utf-8",
        )
        self.right.write_text(
            "transaction,symbol,buyer,seller,quantity,rate,amount,date\n"
            "C1,NABIL,11,22,2,100,200,2026-11-24\n",
            encoding="utf-8",
        )
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({
            "source_revisions": {
                "samir": {"repository": "SamirWagle/Nepse-All-Scraper", "commit": "a" * 40},
                "socrateai": {"repository": "socrateai-official/nepse-open-data", "commit": "b" * 40},
            },
            "pairs": [{
                "trade_date": "2026-11-24",
                "left_path": "left.csv", "left_format": "samir",
                "left_sha256": hashlib.sha256(self.left.read_bytes()).hexdigest(),
                "right_path": "right.csv", "right_format": "socrate",
                "right_sha256": hashlib.sha256(self.right.read_bytes()).hexdigest(),
            }],
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_duplicate_rows_are_preserved_with_occurrence_evidence(self):
        report = duplicate_ledger(self.manifest)
        self.assertEqual(report["duplicate_contract_id_count"], 1)
        self.assertEqual(report["duplicate_physical_row_count"], 2)
        self.assertEqual(report["duplicate_extra_row_count"], 1)
        self.assertTrue(all(x["duplicate_rows_identical"] for x in report["entries"]))
        self.assertEqual([x["occurrence_index"] for x in report["entries"]], [1, 2])
        self.assertEqual([x["physical_csv_line_number"] for x in report["entries"]], [2, 3])
        self.assertFalse(report["training_eligible"])

    def test_hash_mismatch_fails_closed(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["pairs"][0]["left_sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            duplicate_ledger(self.manifest)

    def test_csv_keeps_raw_row_payload(self):
        report = duplicate_ledger(self.manifest)
        output = self.root / "duplicates.csv"
        write_csv(output, report)
        self.assertIn("unresolved_duplicate_contract_id_no_auto_deduplication", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

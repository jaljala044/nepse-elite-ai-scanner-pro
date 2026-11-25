import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_floorsheet_malformed_rows import inspect_manifest, write_csv


class MalformedFloorsheetRowAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.left = self.root / "left.csv"
        self.right = self.root / "right.csv"
        self.left.write_text(
            "date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
            "2026-11-24,1,C1,NABIL,11,22,2,100,200\n",
            encoding="utf-8",
        )
        self.right.write_text(
            "transaction,symbol,buyer,seller,quantity,rate,amount,date\n"
            "C1,NABIL,11,,2,100,200,2026-11-24\n",
            encoding="utf-8",
        )
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({
            "source_revisions": {},
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

    def test_malformed_row_retains_reason_and_physical_line(self):
        report = inspect_manifest(self.manifest)
        self.assertEqual(report["malformed_row_count"], 1)
        row = report["entries"][0]
        self.assertEqual(row["physical_csv_line_number"], 2)
        self.assertIn("blank_fields:seller", row["reasons"])
        self.assertFalse(report["training_eligible"])

    def test_hash_mismatch_fails_closed(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["pairs"][0]["right_sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            inspect_manifest(self.manifest)

    def test_csv_export_keeps_raw_row(self):
        report = inspect_manifest(self.manifest)
        output = self.root / "malformed.csv"
        write_csv(output, report)
        self.assertIn("unresolved_malformed_source_row_no_auto_repair", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

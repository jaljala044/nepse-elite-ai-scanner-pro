import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from analyze_floorsheet_broker_code_coverage import analyze_broker_coverage, write_activity_csv


class BrokerCodeCoverageTests(unittest.TestCase):
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
            "C1,NABIL,11,33,2,100,200,2026-11-24\n",
            encoding="utf-8",
        )
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({
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

    def test_raw_code_coverage_is_counted_without_identity_inference(self):
        report = analyze_broker_coverage(self.manifest)
        day = report["results"][0]
        self.assertEqual(day["shared_codes"], ["11"])
        self.assertEqual(day["samir_only_codes"], ["22"])
        self.assertEqual(day["socrateai_only_codes"], ["33"])
        self.assertFalse(report["broker_legal_identity_verified"])
        self.assertEqual(day["samir"]["buyer_counts"]["11"], 1)
        self.assertEqual(day["socrateai"]["seller_counts"]["33"], 1)

    def test_source_hash_mismatch_fails_closed(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["pairs"][0]["left_sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            analyze_broker_coverage(self.manifest)

    def test_activity_csv_preserves_raw_code_and_side(self):
        report = analyze_broker_coverage(self.manifest)
        output = self.root / "activity.csv"
        write_activity_csv(output, report)
        with output.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 4)
        self.assertIn({"trade_date":"2026-11-24","source":"socrateai","side":"seller","broker_code":"33","contract_side_observations":"1"}, rows)


if __name__ == "__main__":
    unittest.main()

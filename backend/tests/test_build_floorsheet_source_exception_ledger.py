import json
import tempfile
import unittest
from pathlib import Path

from build_floorsheet_source_exception_ledger import build_ledger, write_csv


class FloorsheetExceptionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = self.root / "report.json"
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({
            "source_revisions": {
                "samir": {"repository": "SamirWagle/Nepse-All-Scraper", "commit": "a" * 40},
                "socrateai": {"repository": "socrateai-official/nepse-open-data", "commit": "b" * 40},
            },
            "pairs": [{
                "trade_date": "2026-11-24",
                "left_sha256": "1" * 64,
                "right_sha256": "2" * 64,
            }],
        }), encoding="utf-8")
        self.report.write_text(json.dumps({
            "results": [{
                "trade_date": "2026-11-24",
                "comparison": {
                    "left_source": {"source_path": "left.csv", "sha256": "1" * 64},
                    "right_source": {"source_path": "right.csv", "sha256": "2" * 64},
                    "comparison": {
                        "left_only_contracts": [],
                        "right_only_contracts": [{
                            "contract_id": "C2", "symbol": "NABIL", "buyer": "11",
                            "seller": "22", "quantity": "2", "rate": "100", "amount": "200",
                        }],
                        "conflicts": [],
                    },
                },
            }],
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_source_only_row_is_linked_to_both_pinned_sources(self):
        ledger = build_ledger(self.report, self.manifest)
        self.assertEqual(ledger["exception_count"], 1)
        row = ledger["entries"][0]
        self.assertEqual(row["source_repository"], "socrateai-official/nepse-open-data")
        self.assertEqual(row["other_source_repository"], "SamirWagle/Nepse-All-Scraper")
        self.assertEqual(row["contract_id"], "C2")
        self.assertEqual(row["disposition"], "unresolved_source_only_no_auto_selection")
        self.assertFalse(ledger["training_eligible"])

    def test_manifest_hash_mismatch_fails_closed(self):
        data = json.loads(self.report.read_text(encoding="utf-8"))
        data["results"][0]["comparison"]["right_source"]["sha256"] = "3" * 64
        self.report.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source hash linkage mismatch"):
            build_ledger(self.report, self.manifest)

    def test_csv_export_keeps_record_payloads(self):
        ledger = build_ledger(self.report, self.manifest)
        target = self.root / "ledger.csv"
        write_csv(target, ledger)
        text = target.read_text(encoding="utf-8")
        self.assertIn("C2", text)
        self.assertIn("unresolved_source_only_no_auto_selection", text)


if __name__ == "__main__":
    unittest.main()

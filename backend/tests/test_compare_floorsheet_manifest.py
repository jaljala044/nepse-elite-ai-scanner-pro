import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from compare_floorsheet_manifest import compare_manifest


SAMIR = (
    "date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
    "2026-11-24,1,C1,NABIL,11,22,2,100,200\n"
)
SOCRATE = (
    "transaction,symbol,buyer,seller,quantity,rate,amount,date\n"
    "C1,NABIL,11,22,2,100,200,2026-11-24\n"
)


class FloorsheetManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        (self.base / "left.csv").write_text(SAMIR, encoding="utf-8")
        (self.base / "right.csv").write_text(SOCRATE, encoding="utf-8")
        self.manifest = self.base / "manifest.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, pairs):
        self.manifest.write_text(json.dumps({"pairs": pairs}), encoding="utf-8")

    def pair(self):
        return {
            "trade_date": "2026-11-24",
            "left_path": "left.csv",
            "left_format": "samir",
            "right_path": "right.csv",
            "right_format": "socrate",
        }

    def test_exact_date_pair_reports_hashes_and_never_promotes(self):
        self.write_manifest([self.pair()])
        result = compare_manifest(self.manifest)
        self.assertEqual(result["date_count"], 1)
        self.assertEqual(result["exact_contract_set_and_row_match_dates"], 1)
        self.assertEqual(result["readiness_status"], "review_only_exact_comparison_no_canonical_promotion")
        self.assertFalse(result["canonical_source_selected"])
        self.assertEqual(len(result["results"][0]["left_sha256"]), 64)

    def test_expected_hash_mismatch_fails_closed(self):
        pair = self.pair()
        pair["left_sha256"] = "0" * 64
        self.write_manifest([pair])
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            compare_manifest(self.manifest)

    def test_path_traversal_is_rejected(self):
        pair = self.pair()
        pair["left_path"] = "../outside.csv"
        self.write_manifest([pair])
        with self.assertRaisesRegex(ValueError, "inside the manifest directory"):
            compare_manifest(self.manifest)

    def test_duplicate_dates_are_rejected(self):
        self.write_manifest([self.pair(), self.pair()])
        with self.assertRaisesRegex(ValueError, "duplicate trade_date"):
            compare_manifest(self.manifest)

    def test_invalid_calendar_date_is_rejected(self):
        pair = self.pair()
        pair["trade_date"] = "2026-02-30"
        self.write_manifest([pair])
        with self.assertRaisesRegex(ValueError, "real YYYY-MM-DD"):
            compare_manifest(self.manifest)

    def test_control_date_must_match_pair(self):
        pair = self.pair()
        pair["independent_control"] = {
            "trade_date": "2026-11-23",
            "quantity": "2",
            "gross_amount": "200",
        }
        self.write_manifest([pair])
        with self.assertRaisesRegex(ValueError, "must match pair date"):
            compare_manifest(self.manifest)


if __(!"").isArray) {}

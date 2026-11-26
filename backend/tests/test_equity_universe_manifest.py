import csv
import unittest
from pathlib import Path

from app.equity_universe_manifest import validate_equity_manifest_rows


class EquityUniverseManifestTests(unittest.TestCase):
    def valid_rows(self):
        return [
            {
                "symbol": "AAA", "security_id": "101", "security_name": "AAA Limited",
                "sector": "Commercial Banks", "instrument_type": "Equity", "status": "Active",
                "observed_on": "2026-11-26", "source": "NepseAlpha",
                "source_url": "https://nepsealpha.com/traded-stocks/",
                "source_snapshot_sha256": "a" * 64,
            },
            {
                "symbol": "BBB", "security_id": "102", "security_name": "BBB Limited",
                "sector": "Hydro Power", "instrument_type": "Equity", "status": "Active",
                "observed_on": "2026-11-26", "source": "NepseAlpha",
                "source_url": "https://nepsealpha.com/traded-stocks/",
                "source_snapshot_sha256": "a" * 64,
            },
        ]

    def test_candidate_manifest_is_281_unique_active_equities(self):
        root = Path(__file__).resolve().parents[2]
        path = root / "data/reference/nepse_active_equity_manifest_2026-11-26.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        result = validate_equity_manifest_rows(rows)
        self.assertEqual(result["record_count"], 281)
        self.assertEqual(result["unique_symbol_count"], 281)
        self.assertEqual(result["unique_security_id_count"], 281)
        self.assertFalse(result["membership_authoritatively_verified"])
        self.assertFalse(result["promotion_allowed"])
        symbols = {row["symbol"] for row in rows}
        self.assertTrue({"NESDO", "ULBSL", "YMHL"}.issubset(symbols))
        self.assertNotIn("NICEF", symbols)

    def test_duplicate_symbol_rejected(self):
        rows = self.valid_rows()
        rows[1]["symbol"] = "AAA"
        with self.assertRaisesRegex(ValueError, "duplicate symbols"):
            validate_equity_manifest_rows(rows, expected_count=2)

    def test_duplicate_security_id_rejected(self):
        rows = self.valid_rows()
        rows[1]["security_id"] = "101"
        with self.assertRaisesRegex(ValueError, "duplicate security_ids"):
            validate_equity_manifest_rows(rows, expected_count=2)

    def test_mutual_fund_and_promoter_rows_rejected(self):
        for instrument_type in ("Mutual Fund", "Promoter Share", "Debenture"):
            rows = self.valid_rows()
            rows[0]["instrument_type"] = instrument_type
            with self.subTest(instrument_type=instrument_type):
                with self.assertRaisesRegex(ValueError, "Equity only"):
                    validate_equity_manifest_rows(rows, expected_count=2)

    def test_inactive_rows_rejected(self):
        rows = self.valid_rows()
        rows[0]["status"] = "Suspended"
        with self.assertRaisesRegex(ValueError, "Active records only"):
            validate_equity_manifest_rows(rows, expected_count=2)

    def test_mixed_source_snapshot_hash_rejected(self):
        rows = self.valid_rows()
        rows[1]["source_snapshot_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "one source snapshot hash"):
            validate_equity_manifest_rows(rows, expected_count=2)

    def test_noncanonical_symbol_rejected(self):
        rows = self.valid_rows()
        rows[0]["symbol"] = " aaa "
        with self.assertRaisesRegex(ValueError, "trimmed uppercase"):
            validate_equity_manifest_rows(rows, expected_count=2)

    def test_count_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            validate_equity_manifest_rows(self.valid_rows())


if __name__ == "__main__":
    unittest.main()

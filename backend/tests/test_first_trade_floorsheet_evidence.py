from __future__ import annotations

import unittest
from pathlib import Path

from app.first_trade_floorsheet_evidence import load_first_trade_evidence, validate_first_trade_floorsheet_evidence

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data/reference/nepse_first_trade_floorsheet_evidence_pilot_2025.csv"
EXPECTED = {"GMLI", "NMIC", "CREST", "OMPL", "PURE", "TTL", "SANVI", "BHCL", "HIMSTAR", "MABEL", "DHEL", "SAGAR", "BUNGAL", "BANDIPUR", "SWASTIK", "JHAPA", "SAIL", "SYPNL"}


class FirstTradeFloorsheetEvidenceTests(unittest.TestCase):
    def test_real_pilot_register_remains_pending_without_official_contracts(self):
        report = load_first_trade_evidence(PILOT, expected_symbols=EXPECTED)
        self.assertEqual(report["row_count"], 18)
        self.assertEqual(report["verified_contract_match_count"], 0)
        self.assertEqual(report["pending_count"], 18)
        self.assertFalse(report["exchange_execution_verified"])
        self.assertFalse(report["backtest_admission_allowed"])

    def test_official_contract_match_requires_complete_provenance(self):
        row = {
            "security_id": "9246", "symbol": "GMLI",
            "reported_first_trade_date": "2025-02-09", "archive_first_row_date": "2025-02-09",
            "first_archive_row_volume": "490", "prior_evidence_status": "secondary_source_archive_match",
            "official_floorsheet_status": "verified_contract_match",
            "official_source_id": "NEPSE_OFFICIAL_FLOORSHEET",
            "official_source_url": "https://nepalstock.com.np/floorsheet",
            "raw_response_sha256": "a" * 64, "contract_id": "123456",
            "contract_date": "2025-02-09", "contract_quantity": "490",
            "verified_at_utc": "2026-11-27T19:00:00Z", "notes": "contract independently matched",
        }
        report = validate_first_trade_floorsheet_evidence([row], expected_symbols={"GMLI"})
        self.assertEqual(report["verified_contract_match_count"], 1)
        self.assertTrue(report["exchange_execution_verified"])
        self.assertFalse(report["backtest_admission_allowed"])

    def test_secondary_source_cannot_be_claimed_as_official_contract(self):
        row = {
            "security_id": "9246", "symbol": "GMLI",
            "reported_first_trade_date": "2025-02-09", "archive_first_row_date": "2025-02-09",
            "first_archive_row_volume": "490", "prior_evidence_status": "secondary_source_archive_match",
            "official_floorsheet_status": "verified_contract_match",
            "official_source_id": "MEROLAGANI", "official_source_url": "https://merolagani.com/example",
            "raw_response_sha256": "a" * 64, "contract_id": "123456",
            "contract_date": "2025-02-09", "contract_quantity": "490",
            "verified_at_utc": "2026-11-27T19:00:00Z", "notes": "not official",
        }
        report = validate_first_trade_floorsheet_evidence([row], expected_symbols={"GMLI"})
        self.assertEqual(report["verified_contract_match_count"], 0)
        self.assertTrue(any("requires_official_nepse_source" in error for error in report["errors"]))

    def test_sail_boundary_conflict_cannot_be_promoted(self):
        row = {
            "security_id": "9301", "symbol": "SAIL",
            "reported_first_trade_date": "2025-11-23", "archive_first_row_date": "2025-11-24",
            "first_archive_row_volume": "250", "prior_evidence_status": "quarantined_boundary_mismatch",
            "official_floorsheet_status": "verified_contract_match",
            "official_source_id": "NEPSE_OFFICIAL_FLOORSHEET",
            "official_source_url": "https://nepalstock.com.np/floorsheet",
            "raw_response_sha256": "b" * 64, "contract_id": "SAIL-1",
            "contract_date": "2025-11-23", "contract_quantity": "250",
            "verified_at_utc": "2026-11-27T19:00:00Z", "notes": "first trade",
        }
        report = validate_first_trade_floorsheet_evidence([row], expected_symbols={"SAIL"})
        self.assertEqual(report["verified_contract_match_count"], 0)
        self.assertTrue(any("boundary_conflict" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()

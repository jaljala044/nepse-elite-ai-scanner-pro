from __future__ import annotations

import unittest

from app.floorsheet_coverage import build_floorsheet_coverage_manifest


HASH = "a" * 64


def fixtures():
    sessions = [{"date": "2026-11-23", "status": "confirmed_open",
                 "source_id": "calendar-1", "source_payload_sha256": HASH}]
    instruments = [
        {"symbol": "AAA", "effective_from": "2020-01-01", "status": "verified",
         "as_of_status": "verified", "source_id": "master-1", "source_payload_sha256": HASH},
        {"symbol": "BBB", "effective_from": "2020-01-01", "status": "verified",
         "as_of_status": "verified", "source_id": "master-1", "source_payload_sha256": HASH},
    ]
    daily = [{"date": "2026-11-23", "capture_status": "complete_verified",
              "control_status": "reconciled", "source_id": "floor-1",
              "source_payload_sha256": HASH, "source_row_count": 1,
              "unique_contract_count": 1}]
    contracts = [{"date": "2026-11-23", "symbol": "AAA", "contract_count": 1,
                  "row_validation_status": "verified"}]
    return sessions, instruments, daily, contracts


class FloorsheetCoverageTests(unittest.TestCase):
    def test_positive_contract_is_traded_and_absence_is_confirmed_zero_only_with_full_evidence(self):
        args = fixtures()
        report = build_floorsheet_coverage_manifest(*args)
        cells = {(x["date"], x["symbol"]): x for x in report["cells"]}
        self.assertEqual(cells[("2026-11-23", "AAA")]["status"], "TRADED")
        self.assertEqual(cells[("2026-11-23", "BBB")]["status"], "NO_TRADE")
        self.assertEqual(cells[("2026-11-23", "BBB")]["contract_count"], 0)
        self.assertTrue(report["coverage_complete"])
        self.assertFalse(report["canonical_promotion_allowed"])

    def test_missing_daily_capture_keeps_absence_unknown(self):
        sessions, instruments, _, contracts = fixtures()
        report = build_floorsheet_coverage_manifest(sessions, instruments, [], contracts)
        by_symbol = {x["symbol"]: x for x in report["cells"]}
        self.assertEqual(by_symbol["AAA"]["status"], "UNKNOWN")
        self.assertEqual(by_symbol["BBB"]["status"], "UNKNOWN")
        self.assertFalse(report["coverage_complete"])

    def test_partial_or_unreconciled_daily_capture_never_proves_zero(self):
        sessions, instruments, daily, contracts = fixtures()
        daily[0]["capture_status"] = "partial"
        report = build_floorsheet_coverage_manifest(sessions, instruments, daily, contracts)
        by_symbol = {x["symbol"]: x for x in report["cells"]}
        self.assertEqual(by_symbol["AAA"]["status"], "UNKNOWN")
        self.assertEqual(by_symbol["BBB"]["status"], "UNKNOWN")

    def test_closed_or_unverified_session_keeps_no_row_unknown(self):
        sessions, instruments, daily, contracts = fixtures()
        sessions[0]["status"] = "unknown"
        report = build_floorsheet_coverage_manifest(sessions, instruments, daily, contracts)
        self.assertTrue(all(x["status"] == "UNKNOWN" for x in report["cells"]))

    def test_inactive_instrument_not_classified_as_zero(self):
        sessions, instruments, daily, contracts = fixtures()
        instruments[1]["effective_to"] = "2026-11-20"
        report = build_floorsheet_coverage_manifest(sessions, instruments, daily, contracts)
        by_symbol = {x["symbol"]: x for x in report["cells"]}
        self.assertEqual(by_symbol["BBB"]["status"], "UNKNOWN")

    def test_duplicate_contract_observation_rejected(self):
        args = fixtures()
        args[3].append(dict(args[3][0]))
        with self.assertRaises(ValueError):
            build_floorsheet_coverage_manifest(*args)

    def test_invalid_hash_and_unverified_contracts_rejected(self):
        args = fixtures()
        args[2][0]["source_payload_sha256"] = "bad"
        report = build_floorsheet_coverage_manifest(*args)
        self.assertEqual({x["status"] for x in report["cells"]}, {"UNKNOWN"})
        args = fixtures()
        args[3][0]["row_validation_status"] = "unverified"
        with self.assertRaises(ValueError):
            build_floorsheet_coverage_manifest(*args)


if __name__ == "__main__":
    unittest.main()

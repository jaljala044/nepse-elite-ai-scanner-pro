from __future__ import annotations

import unittest
from pathlib import Path

from app.historical_pilot_cohort import (
    CANDIDATE,
    QUARANTINED,
    load_lifecycle_pilot_cohort,
    validate_lifecycle_pilot_rows,
)

ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT / "data" / "reference" / "nepse_lifecycle_pilot_cohort_2025.csv"


class LifecyclePilotCohortTests(unittest.TestCase):
    def test_committed_cohort_is_valid_but_not_promotable(self):
        report = load_lifecycle_pilot_cohort(COHORT)
        self.assertEqual(report["cohort_count"], 18)
        self.assertEqual(report["candidate_count"], 17)
        self.assertEqual(report["quarantined_count"], 1)
        self.assertFalse(report["exchange_execution_verified"])
        self.assertFalse(report["canonical_promotion_allowed"])
        self.assertFalse(report["backtest_admission_allowed"])
        self.assertFalse(report["production_enabled"])

    def test_sail_boundary_is_preserved_as_quarantined(self):
        report = load_lifecycle_pilot_cohort(COHORT)
        sail = next(row for row in report["rows"] if row["symbol"] == "SAIL")
        self.assertEqual(sail["reported_first_trade_date"], "2025-11-23")
        self.assertEqual(sail["archive_first_row_date"], "2025-11-24")
        self.assertEqual(sail["disposition"], QUARANTINED)

    def test_candidate_date_mismatch_is_rejected(self):
        rows = [{
            "symbol": "TEST",
            "reported_first_trade_date": "2025-01-01",
            "archive_first_row_date": "2025-01-02",
            "first_row_volume": "10",
            "evidence_tier": "secondary_provider_plus_archive_observation",
            "disposition": CANDIDATE,
            "evidence_basis": "secondary report and archive",
            "notes": "test",
        }]
        with self.assertRaisesRegex(ValueError, "dates disagree"):
            validate_lifecycle_pilot_rows(rows, expected_count=1)

    def test_duplicate_symbols_are_rejected(self):
        report = load_lifecycle_pilot_cohort(COHORT)
        rows = []
        for item in report["rows"]:
            rows.append({
                **item,
                "evidence_tier": "secondary_provider_plus_archive_observation",
                "evidence_basis": "secondary report and archive",
                "notes": "test",
            })
        rows[-1]["symbol"] = rows[0]["symbol"]
        with self.assertRaisesRegex(ValueError, "duplicate symbol"):
            validate_lifecycle_pilot_rows(rows, expected_count=18)

    def test_unknown_disposition_is_rejected(self):
        report = load_lifecycle_pilot_cohort(COHORT)
        rows = []
        for item in report["rows"]:
            rows.append({
                **item,
                "evidence_tier": "secondary_provider_plus_archive_observation",
                "evidence_basis": "secondary report and archive",
                "notes": "test",
            })
        rows[0]["disposition"] = "backtest_ready"
        with self.assertRaisesRegex(ValueError, "unsupported disposition"):
            validate_lifecycle_pilot_rows(rows)


if __name__ == "__main__":
    unittest.main()

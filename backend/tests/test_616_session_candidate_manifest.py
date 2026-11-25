from __future__ import annotations

import unittest
from pathlib import Path

from audit_616_session_candidate_manifest import audit_candidates


class Nepse616SessionCandidateAuditTests(unittest.TestCase):
    def test_pinned_candidate_set_passes_structural_reconciliation(self):
        repo_root = Path(__file__).resolve().parents[2]
        result = audit_candidates(repo_root)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["candidate_count"], 616)
        self.assertEqual(result["unique_candidate_date_count"], 616)
        self.assertEqual(result["annual_candidate_counts"], {
            "2024": 189, "2025": 225, "2026": 202,
        })
        self.assertEqual(result["index_date_file_count"], 614)
        self.assertEqual(result["index_date_file_missing"], [
            "2025-04-03", "2026-11-20",
        ])
        self.assertEqual(result["weekday_regime_violation_count"], 0)
        self.assertEqual(result["candidate_holiday_overlap_count"], 0)

    def test_candidate_audit_never_promotes_calendar_or_training(self):
        repo_root = Path(__file__).resolve().parents[2]
        result = audit_candidates(repo_root)
        self.assertFalse(result["canonical_calendar_promotion_allowed"])
        self.assertFalse(result["training_allowed"])


if __name__ == "__main__":
    unittest.main()

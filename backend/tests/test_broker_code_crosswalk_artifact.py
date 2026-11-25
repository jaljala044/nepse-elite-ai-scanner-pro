import csv
import unittest
from pathlib import Path


class BrokerCodeCrosswalkArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parents[2]
        path = repo_root / "data" / "reference" / "broker_code_crosswalk_candidates_2026-11-25.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_91_distinct_codes_match_cds_clearing_member_numbers(self):
        codes = [row["broker_code"] for row in self.rows]
        cm_numbers = [row["cdsc_cm_number"] for row in self.rows]
        self.assertEqual(len(self.rows), 91)
        self.assertEqual(len(set(codes)), 91)
        self.assertEqual(set(codes), set(cm_numbers))

    def test_every_candidate_was_observed_in_both_pinned_sources(self):
        self.assertTrue(all(row["observed_in_samir_2026_11_24"] == "true" for row in self.rows))
        self.assertTrue(all(row["observed_in_socrateai_2026_11_24"] == "true" for row in self.rows))

    def test_candidate_rows_are_not_marked_verified(self):
        self.assertTrue(all(
            row["crosswalk_status"] == "directory_number_match_candidate_not_effective_dated_identity_verification"
            for row in self.rows
        ))

    def test_known_legacy_name_notes_are_preserved(self):
        rows = {row["broker_code"]: row for row in self.rows}
        self.assertIn("Ashutosh", rows["8"]["alias_or_name_history_note"])
        self.assertIn("CBIL", rows["91"]["alias_or_name_history_note"])
        self.assertIn("Citizens", rows["91"]["cdsc_directory_name"])


if __name__ == "__main__":
    unittest.main()

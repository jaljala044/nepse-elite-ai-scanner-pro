import csv
import tempfile
import unittest
from pathlib import Path

from scripts.rank_issue5_weekly_closure_batches import (
    HISTORY, SMC, rank_batches, is_weekly_closure,
)

FIELDS = ["repository", "symbol", "previous_date", "current_date", "session_pair_classification"]
CLASSIFICATION = "date_not_listed_in_project_calendar"


class WeeklyClosureSelectorTests(unittest.TestCase):
    def write_csv(self, path, fields, rows):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def row(self, repository, symbol, previous, current):
        return {
            "repository": repository, "symbol": symbol,
            "previous_date": previous, "current_date": current,
            "session_pair_classification": CLASSIFICATION,
        }

    def test_checked_in_exclusion_register_has_unique_prior_review_dates(self):
        register = (
            Path(__file__).resolve().parents[1]
            / "data" / "reference" / "issue5_registered_weekly_closure_dates.csv"
        )
        from scripts.rank_issue5_weekly_closure_batches import load_exclusions
        excluded = load_exclusions(register)
        self.assertEqual(len(excluded), 20)

    def test_weekday_regime_transition(self):
        from datetime import date
        self.assertTrue(is_weekly_closure(date(2026, 4, 3)))  # Friday, old regime
        self.assertTrue(is_weekly_closure(date(2026, 4, 4)))  # Saturday, old regime
        self.assertFalse(is_weekly_closure(date(2026, 4, 5))) # Sunday, old regime
        self.assertTrue(is_weekly_closure(date(2026, 4, 11))) # Saturday, new regime
        self.assertTrue(is_weekly_closure(date(2026, 4, 12))) # Sunday, new regime
        self.assertFalse(is_weekly_closure(date(2026, 4, 10)))# Friday, new regime

    def test_rank_excludes_registered_dates_and_counts_unique_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                self.row(SMC, "abc", "2026-04-10", "2026-04-11"),
                self.row(HISTORY, "ABC", "2026-04-10", "2026-04-11"),
                self.row(SMC, "XYZ", "2026-04-10", "2026-04-11"),
                self.row(HISTORY, "XYZ", "2026-04-10", "2026-04-11"),
                self.row(SMC, "ABC", "2026-04-11", "2026-04-12"),
                self.row(HISTORY, "ABC", "2026-04-11", "2026-04-12"),
            ]
            candidate = self.write_csv(root / "candidates.csv", FIELDS, rows)
            exclusion = self.write_csv(root / "excluded.csv", ["current_date"], [
                {"current_date": "2026-04-12"},
            ])
            report = rank_batches(candidate, exclusion, 5)
            self.assertEqual(report["selected_date_count"], 1)
            self.assertEqual(report["selected"][0]["current_date"], "2026-04-11")
            self.assertEqual(report["selected"][0]["candidate_pairs"], 4)
            self.assertEqual(report["selected"][0]["unique_symbols"], 2)
            self.assertFalse(report["canonical_or_training_promotion"])
            self.assertFalse(report["raw_source_modified"])

    def test_duplicate_source_symbol_date_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.row(SMC, "ABC", "2026-04-10", "2026-04-11")
            candidate = self.write_csv(root / "candidates.csv", FIELDS, [row, row])
            exclusion = self.write_csv(root / "excluded.csv", ["current_date"], [])
            with self.assertRaisesRegex(ValueError, "duplicate repository/symbol/date"):
                rank_batches(candidate, exclusion)

    def test_unknown_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = self.write_csv(root / "candidates.csv", FIELDS, [
                self.row("untrusted/repo", "ABC", "2026-04-10", "2026-04-11"),
            ])
            exclusion = self.write_csv(root / "excluded.csv", ["current_date"], [])
            with self.assertRaisesRegex(ValueError, "unknown repository"):
                rank_batches(candidate, exclusion)

    def test_noncanonical_date_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = self.write_csv(root / "candidates.csv", FIELDS, [
                self.row(SMC, "ABC", "2026-4-10", "2026-04-11"),
            ])
            exclusion = self.write_csv(root / "excluded.csv", ["current_date"], [])
            with self.assertRaisesRegex(ValueError, "invalid previous_date"):
                rank_batches(candidate, exclusion)

    def test_blank_symbol_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = self.write_csv(root / "candidates.csv", FIELDS, [
                self.row(SMC, "   ", "2026-04-10", "2026-04-11"),
            ])
            exclusion = self.write_csv(root / "excluded.csv", ["current_date"], [])
            with self.assertRaisesRegex(ValueError, "blank symbol"):
                rank_batches(candidate, exclusion)

    def test_non_weekly_closure_is_not_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                self.row(SMC, "ABC", "2026-04-09", "2026-04-10"),
                self.row(HISTORY, "ABC", "2026-04-09", "2026-04-10"),
            ]
            candidate = self.write_csv(root / "candidates.csv", FIELDS, rows)
            exclusion = self.write_csv(root / "excluded.csv", ["current_date"], [])
            report = rank_batches(candidate, exclusion)
            self.assertEqual(report["selected_date_count"], 0)


if __name__ == "__main__":
    unittest.main()

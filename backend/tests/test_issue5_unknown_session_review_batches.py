import csv
import unittest
from datetime import date
from pathlib import Path


class Issue5UnknownSessionBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        path = root / "data" / "reports" / "issue5_next_five_date_batches_2026-11-28.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_exactly_five_distinct_candidate_dates_are_retained(self):
        self.assertEqual(len(self.rows), 5)
        dates = [row["current_date"] for row in self.rows]
        self.assertEqual(len(set(dates)), 5)
        self.assertEqual(dates, ["2026-06-21", "2026-06-06", "2026-06-07", "2026-03-20", "2026-03-21"])

    def test_every_date_is_explicitly_unknown_and_non_promotable(self):
        for row in self.rows:
            with self.subTest(day=row["current_date"]):
                self.assertEqual(row["review_disposition"], "UNKNOWN_EXCHANGE_SESSION")
                self.assertEqual(row["canonical_promotion_allowed"], "false")
                self.assertIn("no direct T1 exchange record retained", row["evidence_tier_limit"])

    def test_candidate_counts_are_positive_and_symbols_bounded(self):
        for row in self.rows:
            with self.subTest(day=row["current_date"]):
                self.assertGreater(int(row["candidate_pairs"]), 0)
                self.assertGreater(int(row["unique_symbols"]), 0)
                self.assertLessEqual(int(row["unique_symbols"]), int(row["candidate_pairs"]))

    def test_weekday_labels_match_gregorian_dates_without_certifying_sessions(self):
        for row in self.rows:
            with self.subTest(day=row["current_date"]):
                self.assertEqual(date.fromisoformat(row["current_date"]).strftime("%A"), row["weekday"])

    def test_weekend_and_holiday_context_never_promotes_exchange_status(self):
        weekend_dates = {"2026-06-21", "2026-06-06", "2026-06-07", "2026-03-21"}
        for row in self.rows:
            if row["current_date"] in weekend_dates:
                self.assertEqual(row["review_disposition"], "UNKNOWN_EXCHANGE_SESSION")
        friday_holiday = next(row for row in self.rows if row["current_date"] == "2026-03-20")
        self.assertEqual(friday_holiday["review_disposition"], "UNKNOWN_EXCHANGE_SESSION")


if __name__ == "__main__":
    unittest.main()

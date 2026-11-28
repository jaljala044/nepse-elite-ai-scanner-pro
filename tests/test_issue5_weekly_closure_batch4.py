import csv
import unittest
from pathlib import Path


class Issue5WeeklyClosureBatch4Tests(unittest.TestCase):
    def test_batch_has_five_dates_and_3225_candidate_pair_incidences(self):
        path = (Path(__file__).resolve().parents[1] / "data" / "reports" /
                "issue5_next_five_weekly_closure_batches_4_2026-11-28.csv")
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 5)
        self.assertEqual(sum(int(row["candidate_pairs"]) for row in rows), 3225)
        self.assertEqual({row["repositories"] for row in rows}, {"2"})
        self.assertTrue(all(row["review_disposition"] == "WEEKLY_CLOSED_AFTER_2026-04-06" for row in rows))
        self.assertTrue(all(row["canonical_promotion_allowed"].lower() == "false" for row in rows))

    def test_date_groups_are_unique_and_have_one_previous_date_each(self):
        path = (Path(__file__).resolve().parents[1] / "data" / "reports" /
                "issue5_next_five_weekly_closure_batches_4_2026-11-28.csv")
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        dates = [row["current_date"] for row in rows]
        self.assertEqual(len(dates), len(set(dates)))
        self.assertTrue(all(row["previous_date"] < row["current_date"] for row in rows))


if __name__ == "__main__":
    unittest.main()

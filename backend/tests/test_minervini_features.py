import unittest
from datetime import date, timedelta

from app.minervini_features import evaluate_minervini_trend


def make_rows(count, rising=True):
    start = date(2025, 1, 1)
    rows = []
    for index in range(count):
        close = 500 + index if rising else 1000 - index
        rows.append({
            "date": (start + timedelta(days=index)).isoformat(),
            "open": close - 1,
            "high": close + 5,
            "low": close - 5,
            "close": close,
        })
    return rows


class MinerviniFeatureTests(unittest.TestCase):
    def test_complete_rising_trend_template(self):
        result = evaluate_minervini_trend(make_rows(252))
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(result["coverage"], 1.0)
        self.assertTrue(all(result["checks"].values()))

    def test_complete_declining_series_fails_template(self):
        result = evaluate_minervini_trend(make_rows(252, rising=False))
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["score"], 0.0)
        self.assertFalse(any(result["checks"].values()))

    def test_incomplete_52_week_history_has_no_component_score(self):
        result = evaluate_minervini_trend(make_rows(220))
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])
        self.assertEqual(result["coverage"], 0.75)
        self.assertIn("within_25_percent_of_52w_high", result["missing_checks"])

    def test_unsorted_rows_are_sorted_before_calculation(self):
        rows = make_rows(252)
        result = evaluate_minervini_trend(list(reversed(rows)))
        self.assertEqual(result["score"], 100.0)

    def test_duplicate_session_date_rejected(self):
        rows = make_rows(252)
        rows[-1]["date"] = rows[-2]["date"]
        with self.assertRaisesRegex(ValueError, "duplicate session date"):
            evaluate_minervini_trend(rows)

    def test_invalid_ohlc_rejected(self):
        rows = make_rows(252)
        rows[-1]["high"] = rows[-1]["close"] - 1
        with self.assertRaisesRegex(ValueError, "OHLC invariant"):
            evaluate_minervini_trend(rows)


if __name__ == "__main__":
    unittest.main()

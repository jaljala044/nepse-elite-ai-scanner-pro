import unittest
from app.walk_forward_report import build_walk_forward_report


class WalkForwardReportTests(unittest.TestCase):
    def test_expanding_folds_use_training_only_baseline(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8},
            {"observation_date":"2026-01-02","actual":0,"probability":0.2},
            {"observation_date":"2026-01-03","actual":1,"probability":0.7},
            {"observation_date":"2026-01-04","actual":0,"probability":0.3},
            {"observation_date":"2026-01-05","actual":1,"probability":0.6},
        ]
        report = build_walk_forward_report(rows, min_train_dates=2, test_dates=1)
        self.assertEqual(report["fold_count"], 3)
        self.assertEqual(report["folds"][0]["train_prevalence_baseline"], 0.5)
        self.assertEqual(report["folds"][0]["test_start"], "2026-01-03")
        self.assertEqual(report["folds"][0]["test_rows"], 1)

    def test_insufficient_history_returns_no_folds(self):
        rows = [{"observation_date":"2026-01-01","actual":1,"probability":0.8}]
        self.assertEqual(build_walk_forward_report(rows, 2, 1)["status"], "insufficient_sample")

    def test_invalid_probability_rejected(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8},
            {"observation_date":"2026-01-02","actual":0,"probability":1.2},
            {"observation_date":"2026-01-03","actual":1,"probability":0.7},
        ]
        with self.assertRaises(ValueError):
            build_walk_forward_report(rows, 1, 2)


if __name__ == "__main__":
    unittest.main()

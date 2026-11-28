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

    def test_fractional_binary_label_rejected_instead_of_truncated(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8},
            {"observation_date":"2026-01-02","actual":0.5,"probability":0.2},
        ]
        with self.assertRaisesRegex(ValueError, "exactly binary"):
            build_walk_forward_report(rows, 1, 1)

    def test_non_finite_probability_rejected(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8},
            {"observation_date":"2026-01-02","actual":0,"probability":float("nan")},
        ]
        with self.assertRaisesRegex(ValueError, "finite"):
            build_walk_forward_report(rows, 1, 1)

    def test_non_iso_observation_date_rejected(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8},
            {"observation_date":"yesterday","actual":0,"probability":0.2},
        ]
        with self.assertRaisesRegex(ValueError, "invalid walk-forward row"):
            build_walk_forward_report(rows, 1, 1)

    def test_invalid_probability_rejected(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8},
            {"observation_date":"2026-01-02","actual":0,"probability":1.2},
            {"observation_date":"2026-01-03","actual":1,"probability":0.7},
        ]
        with self.assertRaises(ValueError):
            build_walk_forward_report(rows, 1, 2)


    def test_quarantined_forecast_rejected(self):
        rows = [{"observation_date":"2026-01-01","actual":1,"probability":0.8,"quarantined":True}]
        with self.assertRaisesRegex(ValueError,"quarantined forecast"):
            build_walk_forward_report(rows,1,1)

    def test_runtime_ledger_rejects_contaminated_constituent(self):
        from unittest.mock import patch
        rows = [{"observation_date":"2026-01-02","actual":1,"probability":0.8,
                 "symbol":"AAA","constituent_sessions":["2026-01-01","2026-01-02"]}]
        with patch("app.walk_forward_report.runtime_quarantine_keys",return_value=frozenset({("AAA","2026-01-01")})):
            with self.assertRaisesRegex(ValueError,"quarantined forecast constituent"):
                build_walk_forward_report(rows,1,1,require_ledger=True)
        with patch("app.walk_forward_report.runtime_quarantine_keys",return_value=frozenset()):
            result = build_walk_forward_report(rows,1,1,require_ledger=True)
            self.assertTrue(result["quarantine_ledger_checked"])
            self.assertFalse(result["approved_backtest_eligible"])
            with self.assertRaisesRegex(ValueError,"missing forecast"):
                build_walk_forward_report([dict(rows[0],constituent_sessions=[])],1,1,require_ledger=True)

    def test_required_ledger_missing_rejects_evaluation(self):
        from unittest.mock import patch
        with patch("app.walk_forward_report.runtime_quarantine_keys",side_effect=ValueError("pinned quarantine ledger required")):
            with self.assertRaisesRegex(ValueError,"pinned quarantine ledger"):
                build_walk_forward_report([],1,1,require_ledger=True)


if __name__ == "__main__":
    unittest.main()

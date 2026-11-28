import unittest
from app.scenario_validation import validate_binary_forecasts, walk_forward_splits


class ScenarioValidationTests(unittest.TestCase):
    def test_probability_metrics_and_prevalence_baseline(self):
        result = validate_binary_forecasts([0,1,1,0], [0.1,0.8,0.7,0.4])
        self.assertEqual(result["sample_count"], 4)
        self.assertLess(result["brier_score"], result["constant_prevalence_baseline_brier"])

    def test_empty_sample_is_not_scored(self):
        self.assertEqual(validate_binary_forecasts([], [])["status"], "insufficient_sample")

    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_binary_forecasts([1], [1.2])

    def test_walk_forward_folds_are_chronological_and_non_overlapping(self):
        dates = [f"2026-11-{i:02d}" for i in range(1,11)]
        folds = walk_forward_splits(dates, min_train=4, test_size=2)
        self.assertEqual(len(folds), 3)
        self.assertLess(folds[0]["train_end"], folds[0]["test_start"])
        self.assertLess(folds[0]["test_end"], folds[1]["test_start"])

    def test_insufficient_dates_returns_no_fold(self):
        self.assertEqual(walk_forward_splits(["2026-11-01","2026-11-02"], 2, 2), [])


    def test_strict_numeric_and_chronological_inputs(self):
        for label in (True, 0.5, "1"):
            with self.assertRaises(ValueError):
                validate_binary_forecasts([label], [0.5])
        for p in (float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                validate_binary_forecasts([1], [p])
        with self.assertRaises(ValueError):
            walk_forward_splits(["2026-11-01"], 1, 1, 0)
        with self.assertRaises(ValueError):
            walk_forward_splits(["20261101"], 1, 1)

    def test_ledger_lineage_contract(self):
        from unittest.mock import patch
        row = {"symbol":"AAA","constituent_sessions":["2025-07-28"]}
        with patch("app.scenario_validation.runtime_quarantine_keys",return_value=frozenset({("AAA","2025-07-28")})):
            with self.assertRaisesRegex(ValueError,"quarantined forecast constituent"):
                validate_binary_forecasts([1],[0.8],lineage=[row],require_ledger=True)
        with patch("app.scenario_validation.runtime_quarantine_keys",return_value=frozenset()):
            for lineage in (None, [], [dict(row,quarantined=True)], [dict(row,constituent_sessions=["2025-07-28"]*2)]):
                with self.assertRaises(ValueError):
                    validate_binary_forecasts([1],[0.8],lineage=lineage,require_ledger=True)
            result = validate_binary_forecasts([1],[0.8],lineage=[row],require_ledger=True)
            self.assertTrue(result["quarantine_ledger_checked"])
            self.assertFalse(result["approved_backtest_eligible"])


if __name__ == "__main__":
    unittest.main()

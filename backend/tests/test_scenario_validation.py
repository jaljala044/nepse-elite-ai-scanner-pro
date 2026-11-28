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

    def test_quarantined_constituent_is_rejected_from_binary_metrics(self):
        lineage = [
            {"symbol": "AAA", "constituent_sessions": ["2026-01-01", "2026-01-03"]},
            {"symbol": "BBB", "constituent_sessions": ["2026-01-02"]},
        ]
        from unittest.mock import patch
        with patch("app.scenario_validation.runtime_quarantine_keys",
                   return_value=frozenset({("AAA", "2026-01-02")})):
            with self.assertRaisesRegex(ValueError, "quarantined forecast constituent session"):
                validate_binary_forecasts([1, 0], [0.8, 0.2], lineage=lineage)

    def test_required_ledger_without_server_configuration_fails_closed(self):
        from unittest.mock import patch
        with patch("app.scenario_validation.runtime_quarantine_keys",
                   side_effect=ValueError("pinned quarantine ledger required")):
            with self.assertRaisesRegex(ValueError, "pinned quarantine ledger required"):
                validate_binary_forecasts([1], [0.8], require_ledger=True)

    def test_lineage_requires_unique_canonical_constituent_sessions(self):
        lineage = [{"symbol": "AAA",
                    "constituent_sessions": ["2026-01-01", "2026-01-01"]}]
        with self.assertRaisesRegex(ValueError, "invalid forecast constituent dates"):
            validate_binary_forecasts([1], [0.8], lineage=lineage)

    def test_walk_forward_folds_are_chronological_and_non_overlapping(self):
        dates = [f"2026-11-{i:02d}" for i in range(1,11)]
        folds = walk_forward_splits(dates, min_train=4, test_size=2)
        self.assertEqual(len(folds), 3)
        self.assertLess(folds[0]["train_end"], folds[0]["test_start"])
        self.assertLess(folds[0]["test_end"], folds[1]["test_start"])

    def test_insufficient_dates_returns_no_fold(self):
        self.assertEqual(walk_forward_splits(["2026-11-01","2026-11-02"], 2, 2), [])


if __name__ == "__main__":
    unittest.main()

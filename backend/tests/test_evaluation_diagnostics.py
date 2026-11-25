import unittest
from app.evaluation_diagnostics import build_evaluation_diagnostics


class EvaluationDiagnosticsTests(unittest.TestCase):
    def row(self, day, actual, probability, label_time=None, input_time=None):
        return {"forecast_id":"F"+day, "observation_date":day,
                "decision_time":day+"T12:00:00Z",
                "max_input_available_at":input_time or day+"T11:00:00Z",
                "label_available_at":label_time or day+"T18:00:00Z",
                "actual":actual, "probability":probability}

    def test_coverage_missing_dates_and_walk_forward_report(self):
        rows = [self.row("2026-01-01",1,0.8), self.row("2026-01-02",0,0.2),
                self.row("2026-01-03",1,0.7), self.row("2026-01-04",0,0.3)]
        report = build_evaluation_diagnostics(rows,
            ["2026-01-01","2026-01-02","2026-01-03","2026-01-04","2026-01-05"], 2, 1)
        self.assertEqual(report["coverage_ratio"], 0.8)
        self.assertEqual(report["missing_decision_dates"], ["2026-01-05"])
        self.assertEqual(report["fold_count"], 2)
        self.assertEqual(report["folds"][0]["train_rows"], 2)

    def test_future_inputs_and_early_known_labels_flagged(self):
        future = self.row("2026-01-01",1,0.8,input_time="2026-01-01T13:00:00Z")
        early_label = self.row("2026-01-02",0,0.2,label_time="2026-01-02T12:00:00Z")
        report = build_evaluation_diagnostics([future,early_label],
            ["2026-01-01","2026-01-02"], 1, 1)
        self.assertEqual(len(report["leakage_exceptions"]), 2)
        self.assertEqual(report["eligible_forecast_count"], 0)

    def test_duplicate_dates_are_not_scored(self):
        rows = [self.row("2026-01-01",1,0.8), self.row("2026-01-01",0,0.2),
                self.row("2026-01-02",1,0.7)]
        report = build_evaluation_diagnostics(rows, ["2026-01-01","2026-01-02"], 1, 1)
        self.assertEqual(report["duplicate_decision_dates"], ["2026-01-01"])
        self.assertEqual(report["eligible_forecast_count"], 1)

    def test_missing_label_is_reported(self):
        row = self.row("2026-01-01",None,0.8)
        report = build_evaluation_diagnostics([row], ["2026-01-01"], 1, 1)
        self.assertEqual(report["missing_label_forecast_ids"], ["F2026-01-01"])


if __name__ == "__main__":
    unittest.main()

import unittest
from app.scanner_research_validation_report import build_research_validation_report

class IntegratedResearchValidationTests(unittest.TestCase):
    def test_rejects_train_validation_or_unlabelled_signals_in_final_report(self):
        with self.assertRaisesRegex(ValueError, "all_signals_must_be_explicit_out_of_sample"):
            build_research_validation_report(replay_bundle={"runs":[]},
                signals=[{"signal_id":"S1","sample_partition":"train"}], fold_results=[])
        with self.assertRaisesRegex(ValueError, "all_replay_runs_must_be_out_of_sample"):
            build_research_validation_report(replay_bundle={"runs":[{"partition":"train"}]},
                signals=[], fold_results=[])
        with self.assertRaisesRegex(ValueError, "all_fold_results_must_be_out_of_sample"):
            build_research_validation_report(replay_bundle={"runs":[]},
                signals=[], fold_results=[{"partition":"validation"}])

    def test_empty_oos_inputs_report_no_selection_not_fake_winner(self):
        result=build_research_validation_report(replay_bundle={"runs":[]},
            signals=[], fold_results=[])
        self.assertEqual(result["partition"], "out_of_sample")
        self.assertEqual(result["selection_summary"]["eligible_strategy_horizon_count"], 0)
        self.assertTrue(all(v is None for v in result["selection_summary"]["horizon_winners"].values()))
        self.assertFalse(result["performance_claimed"])
        self.assertFalse(result["production_enabled"])

if __name__ == "__main__":
    unittest.main()

import unittest
from app.training_readiness import evaluate_training_readiness, REQUIRED_GATES


class TrainingReadinessTests(unittest.TestCase):
    def evidence(self):
        return {**{key: True for key in REQUIRED_GATES},
                "ohlcv_coverage": 0.99, "broker_identity_coverage": 0.97,
                "evidence_snapshot_id": "snapshot-123"}

    def test_all_evidence_and_thresholds_pass(self):
        r = evaluate_training_readiness(self.evidence())
        self.assertTrue(r["training_ready"])
        self.assertTrue(r["model_training_allowed"])

    def test_missing_gate_blocks_training(self):
        e = self.evidence()
        del e["universe_verified"]
        r = evaluate_training_readiness(e)
        self.assertFalse(r["model_training_allowed"])
        self.assertIn("universe_verified", r["blockers"])

    def test_low_coverage_blocks_training(self):
        e = self.evidence()
        e["ohlcv_coverage"] = 0.7
        r = evaluate_training_readiness(e)
        self.assertIn("ohlcv_coverage_threshold", r["blockers"])

    def test_string_true_does_not_pass_boolean_evidence(self):
        e = self.evidence()
        e["source_rights_cleared"] = "true"
        r = evaluate_training_readiness(e)
        self.assertIn("source_rights_cleared", r["blockers"])

    def test_invalid_threshold_rejected(self):
        with self.assertRaisesRegex(ValueError, "between zero and one"):
            evaluate_training_readiness(self.evidence(), minimum_ohlcv_coverage=1.5)

    def test_never_claims_model_performance(self):
        self.assertFalse(evaluate_training_readiness(self.evidence())["model_performance_claimed"])


if __name__ == "__main__":
    unittest.main()

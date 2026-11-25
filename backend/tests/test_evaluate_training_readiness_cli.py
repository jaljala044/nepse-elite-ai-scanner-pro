import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evaluate_training_readiness import evaluate_from_paths


class ReadinessCliTests(unittest.TestCase):
    def write_json(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def args(self, **values):
        defaults = {
            "universe_report": None, "session_reports": None, "provenance_reports": None,
            "ohlcv_report": None, "broker_report": None, "point_in_time_report": None,
            "corporate_action_reviewed": False, "holdout_protocol_id": None,
            "historical_coverage": None, "evidence_snapshot_id": None,
        }
        defaults.update(values)
        return SimpleNamespace(**defaults)

    def test_missing_reports_return_blockers_without_side_effects(self):
        result = evaluate_from_paths(self.args())
        self.assertFalse(result["training_readiness"]["training_ready"])
        self.assertEqual(result["readiness_report_policy"],
                         "read_only_no_canonical_promotion_no_training_execution")

    def test_complete_explicit_reports_can_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.args(
                universe_report=self.write_json(root, "universe.json", {"manifest_verified": True}),
                session_reports=self.write_json(root, "sessions.json", [
                    {"status":"verified","session_state":"confirmed_trading_session"}]),
                provenance_reports=self.write_json(root, "provenance.json", [{
                    "training_eligibility":{"rights_clearance":True},
                    "capture":{"payload_sha256":"a"*64,"source_record_id":"row-1"},
                    "provenance_sha256":"b"*64}]),
                ohlcv_report=self.write_json(root, "ohlcv.json", {
                    "integrity_status":"passed","unresolved_exception_count":0,"coverage_ratio":0.99}),
                broker_report=self.write_json(root, "broker.json", {
                    "identity_policy_status":"passed","unresolved_identity_policy_violations":0,
                    "verified_amount_coverage":0.97}),
                point_in_time_report=self.write_json(root, "pit.json", {
                    "leakage_status":"passed","future_input_count":0,"premature_label_count":0}),
                corporate_action_reviewed=True, holdout_protocol_id="walk-forward-v1",
                historical_coverage=0.99, evidence_snapshot_id="snapshot-1")
            result = evaluate_from_paths(args)
            self.assertTrue(result["training_readiness"]["training_ready"])
            self.assertFalse(result["training_readiness"]["model_performance_claimed"])

    def test_malformed_json_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                evaluate_from_paths(self.args(universe_report=str(path)))


if __name__ == "__main__":
    unittest.main()

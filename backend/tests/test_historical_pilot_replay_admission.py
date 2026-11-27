import unittest
from app.historical_pilot_replay_admission import STRATEGIES, HORIZONS, evaluate_six_scanner_replay_admission


class ReplayAdmissionTests(unittest.TestCase):
    def args(self):
        return dict(
            quality_dashboard={"status":"QUALITY_REVIEW_READY"},
            replay_preflight={"status":"BOUNDED_PILOT_REPLAY_PREFLIGHT_READY","historical_replay_executed":False,"dataset_manifest":{"sha256":"a"*64}},
            strategy_ids=list(STRATEGIES), horizons=list(HORIZONS), dataset_manifest_sha256="a"*64,
            partition="untouched_out_of_sample",
            cost_model={"commission":1,"regulatory_fees":1,"taxes":1,"slippage":1},
            execution_model={"next_session_execution":True,"liquidity_cap":0.05,"settlement_delay":"T+2","stop_first":True,"circuit_and_no_bid_handling":True},
            human_review={"reviewed":True,"approved":True,"reviewer_id":"reviewer-1","reviewed_at":"2026-11-27T10:00:00+05:45"},
        )
    def test_admission_requires_all_gates_and_never_executes(self):
        out=evaluate_six_scanner_replay_admission(**self.args())
        self.assertEqual(out["status"],"ADMITTED_FOR_RESEARCH_REPLAY")
        self.assertEqual(out["handoff"]["strategy_horizon_runs"],24)
        self.assertFalse(out["historical_replay_executed"])
    def test_hash_mismatch_blocks(self):
        args=self.args(); args["dataset_manifest_sha256"]="b"*64
        self.assertIn("dataset_manifest_hash_mismatch",evaluate_six_scanner_replay_admission(**args)["blocking_reasons"])
    def test_in_sample_partition_blocks(self):
        args=self.args(); args["partition"]="validation"
        self.assertIn("replay_partition_must_be_untouched_oos",evaluate_six_scanner_replay_admission(**args)["blocking_reasons"])
    def test_missing_human_approval_blocks(self):
        args=self.args(); args["human_review"]={"reviewed":True,"approved":False}
        self.assertFalse(evaluate_six_scanner_replay_admission(**args)["admitted"])
    def test_incomplete_strategy_set_blocks(self):
        args=self.args(); args["strategy_ids"]=list(STRATEGIES[:-1])
        self.assertIn("six_strategy_set_incomplete_or_duplicate",evaluate_six_scanner_replay_admission(**args)["blocking_reasons"])


if __name__ == "__main__": unittest.main()

import unittest

from app.decision_engine import evaluate_all_horizons, evaluate_horizon


class DecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.stage1 = {
            "eligible": True, "data_quality": "HIGH", "identity_valid": True,
            "session_valid": True, "source_valid": True,
            "corporate_actions_clear": True, "point_in_time_valid": True,
            "liquidity_pass": True, "market_tradeable": True,
        }
        self.stage2 = {
            "components": {
                "wyckoff": 80, "minervini": 85, "relative_strength": 82,
                "broker_footprint": 75, "volume_vsa": 80, "liquidity": 90,
                "sector": 70, "smc": 80,
            },
            "structure": {
                "confirmed_by_horizon": {"SWING": True},
                "entry_trigger": {"SWING": "retest_confirmed"},
            },
        }
        self.plan = {
            "entry_low": 100, "entry_high": 102, "stop_loss": 96,
            "targets": {"t1": 114, "t2": 120, "t3": None},
            "evidence_refs": ["chart:abc"],
        }

    def test_missing_structure_confirmation_fails_closed(self):
        result = evaluate_horizon("TEST", "SWING", self.stage1,
                                  {"components": self.stage2["components"],
                                   "structure": {}},
                                  self.plan, ["ohlcv:1"])
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIn("horizon_specific_structure_confirmation_missing", result["reasons"])

    def test_confirmed_retest_can_buy_with_two_to_one_rr(self):
        result = evaluate_horizon("TEST", "SWING", self.stage1, self.stage2,
                                  self.plan, ["ohlcv:1", "stage2:1"])
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["subtype"], "BUY_AFTER_RETEST")
        self.assertEqual(result["reward_risk"], 2.0)

    def test_missing_stage1_evidence_never_buys(self):
        result = evaluate_horizon("TEST", "SWING", {"eligible": False},
                                  self.stage2, self.plan, ["ohlcv:1"])
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertEqual(result["confidence"], "LOW")

    def test_horizons_are_independent(self):
        plans = {key: self.plan for key in ("T+2", "SWING", "POSITIONAL", "INVESTMENT")}
        results = evaluate_all_horizons("TEST", self.stage1, self.stage2,
                                        plans, ["ohlcv:1", "stage2:1"])
        self.assertEqual(results["SWING"]["action"], "BUY")
        self.assertNotEqual(results["T+2"]["action"], "BUY")


    def test_targets_must_be_strictly_increasing(self):
        bad_plan = dict(self.plan)
        bad_plan["targets"] = {"t1": 114, "t2": 112, "t3": 130}
        result = evaluate_horizon("TEST", "SWING", self.stage1, self.stage2,
                                  bad_plan, ["ohlcv:1", "stage2:1"])
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIsNone(result["entry_zone"])

    def test_malformed_level_evidence_reference_container_fails_closed(self):
        bad_plan = dict(self.plan)
        bad_plan["evidence_refs"] = "not-a-list"
        result = evaluate_horizon("TEST", "SWING", self.stage1, self.stage2,
                                  bad_plan, ["ohlcv:1", "stage2:1"])
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIn("evidence_backed_entry_stop_t1_and_level_references_required",
                      result["reasons"])

    def test_no_trade_does_not_report_high_confidence(self):
        stage2 = {"components": self.stage2["components"], "structure": {}}
        result = evaluate_horizon("TEST", "SWING", self.stage1, stage2,
                                  self.plan, ["ohlcv:1", "stage2:1"])
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertEqual(result["confidence"], "LOW")

    def test_distribution_triggers_sell_for_existing_holder(self):
        stage2 = dict(self.stage2)
        stage2["structure"] = {"distribution_confirmed": True}
        result = evaluate_horizon("TEST", "SWING", self.stage1, stage2,
                                  self.plan, ["ohlcv:1"], holding=True)
        self.assertEqual(result["action"], "SELL")
        self.assertEqual(result["subtype"], "SELL_NOW")


if __name__ == "__main__":
    unittest.main()

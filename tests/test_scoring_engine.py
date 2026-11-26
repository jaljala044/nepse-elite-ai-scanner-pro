import unittest

from app.scoring_engine import COMPONENT_WEIGHTS, score_scan


FULL = {
    "wyckoff": 90,
    "trend": 92,
    "relative_strength": 88,
    "broker": 80,
    "volume": 85,
    "liquidity": 90,
    "sector": 80,
    "smc": 90,
}


def evaluate(components=None, **overrides):
    args = {
        "stage1_quality": "HIGH",
        "structure_confirmed": True,
        "liquidity_ok": True,
        "market_tradeable": True,
        "reward_risk": 2.5,
        "hard_blocks": [],
    }
    args.update(overrides)
    return score_scan(FULL if components is None else components, **args)


class ScoringEngineTests(unittest.TestCase):
    def test_weights_sum_to_one_hundred(self):
        self.assertEqual(sum(COMPONENT_WEIGHTS.values()), 100)

    def test_complete_high_quality_confirmed_setup_can_buy(self):
        result = evaluate()
        self.assertEqual(result["coverage_pct"], 100)
        self.assertEqual(result["coverage_status"], "complete")
        self.assertEqual(result["action"], "BUY")
        self.assertIsNone(result["probability"])

    def test_missing_component_is_not_neutral_and_blocks_buy(self):
        components = dict(FULL, broker=None)
        result = evaluate(components)
        self.assertEqual(result["coverage_pct"], 90)
        self.assertEqual(result["coverage_status"], "provisional")
        self.assertIn("broker", result["missing_components"])
        self.assertTrue(result["rating"].startswith("Provisional"))
        self.assertEqual(result["action"], "WAIT")

    def test_low_coverage_is_no_trade(self):
        result = evaluate({"wyckoff": 80, "trend": 80})
        self.assertEqual(result["coverage_pct"], 50)
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIsNone(result["composite_score"])

    def test_score_normalizes_only_over_available_weights(self):
        result = evaluate({"wyckoff": 80, "trend": 100})
        self.assertEqual(result["composite_score"], 90)
        self.assertEqual(result["available_weight"], 50)

    def test_low_stage1_quality_never_buys(self):
        self.assertEqual(evaluate(stage1_quality="LOW")["action"], "NO_TRADE")

    def test_medium_stage1_quality_waits(self):
        self.assertEqual(evaluate(stage1_quality="MEDIUM")["action"], "WAIT")

    def test_unconfirmed_structure_waits(self):
        self.assertEqual(evaluate(structure_confirmed=False)["action"], "WAIT")

    def test_illiquidity_waits(self):
        self.assertEqual(evaluate(liquidity_ok=False)["action"], "WAIT")

    def test_untradeable_market_waits(self):
        self.assertEqual(evaluate(market_tradeable=False)["action"], "WAIT")

    def test_reward_risk_below_two_blocks_buy(self):
        result = evaluate(reward_risk=1.99)
        self.assertEqual(result["action"], "WAIT")
        self.assertIn("reward_risk_below_2R_or_unavailable", result["buy_blockers"])

    def test_hard_block_forces_no_trade(self):
        result = evaluate(hard_blocks=["distribution_confirmed"])
        self.assertEqual(result["action"], "NO_TRADE")

    def test_invalid_component_score_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(dict(FULL, trend=101))

    def test_boolean_component_score_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(dict(FULL, trend=True))

    def test_unknown_component_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(dict(FULL, momentum=99))

    def test_invalid_reward_risk_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(reward_risk=float("nan"))


if __name__ == "__main__":
    unittest.main()

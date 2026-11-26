import unittest

from app.scoring_engine import build_component_scores, score_feature_bundle


class FeatureBundleAdapterTests(unittest.TestCase):
    def setUp(self):
        self.bundle = {
            "wyckoff": {"status": "observed", "score": 90},
            "trend": {"status": "observed", "score": 80},
            "relative_strength": {"status": "observed", "score": 70},
            "broker": {"status": "observed", "score": 60},
            "volume": {"status": "observed", "score": 50},
            "liquidity": {"status": "observed", "score": 90},
            "sector": {"status": "observed", "score": 80},
            "smc": {"status": "observed", "score": 100},
        }

    def gates(self, **overrides):
        values = {
            "stage1_quality": "HIGH",
            "structure_confirmed": True,
            "liquidity_ok": True,
            "market_tradeable": True,
            "reward_risk": 2.5,
            "hard_blocks": [],
        }
        values.update(overrides)
        return values

    def test_observed_feature_scores_map_to_canonical_components(self):
        result = build_component_scores(self.bundle)
        self.assertEqual(set(result), set(self.bundle))
        self.assertEqual(result["wyckoff"], 90)
        self.assertEqual(result["smc"], 100)

    def test_non_observed_feature_status_is_missing_not_neutral(self):
        bundle = dict(self.bundle)
        bundle["broker"] = {"status": "partial_identity_coverage", "score": 99}
        bundle["smc"] = {"status": "experimental_only", "score": 100}
        result = build_component_scores(bundle)
        self.assertIsNone(result["broker"])
        self.assertIsNone(result["smc"])

    def test_missing_feature_and_missing_score_are_unavailable(self):
        bundle = dict(self.bundle)
        bundle.pop("sector")
        bundle["volume"] = {"status": "observed", "score": None}
        result = build_component_scores(bundle)
        self.assertIsNone(result["sector"])
        self.assertIsNone(result["volume"])

    def test_bundle_scoring_retains_evidence_status_and_blocks_partial_buy(self):
        bundle = dict(self.bundle)
        bundle["broker"] = {"status": "insufficient_evidence", "score": None}
        result = score_feature_bundle(bundle, **self.gates())
        self.assertEqual(result["coverage_pct"], 90)
        self.assertEqual(result["action"], "WAIT")
        self.assertEqual(result["component_evidence_status"]["broker"], "insufficient_evidence")
        self.assertEqual(result["scoring_source"], "observed_upstream_feature_outputs_only")

    def test_bundle_scoring_never_treats_experimental_smc_as_production(self):
        bundle = dict(self.bundle)
        bundle["smc"] = {"status": "experimental_only", "score": 100}
        result = score_feature_bundle(bundle, **self.gates())
        self.assertEqual(result["coverage_pct"], 95)
        self.assertEqual(result["action"], "WAIT")
        self.assertIn("smc", result["missing_components"])

    def test_invalid_observed_score_is_rejected(self):
        bundle = dict(self.bundle)
        bundle["trend"] = {"status": "observed", "score": 101}
        with self.assertRaises(ValueError):
            build_component_scores(bundle)

    def test_unknown_component_is_rejected(self):
        with self.assertRaises(ValueError):
            build_component_scores({"momentum": {"status": "observed", "score": 99}})


if __name__ == "__main__":
    unittest.main()

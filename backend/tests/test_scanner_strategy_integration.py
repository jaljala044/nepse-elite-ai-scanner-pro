import unittest

from app.scanner_strategy_integration import adapt_feature_snapshot_to_strategy_evidence
from app.scanner_strategy_lab import STRATEGIES

CUTOFF = "2026-11-27T12:00:00+05:45"


def snapshot():
    names = {
        "trend": "trend", "relative_strength": "relative_strength",
        "wyckoff": "wyckoff", "volume": "volume", "smc": "smc",
        "liquidity": "liquidity", "sector": "sector", "broker": "broker",
    }
    return {
        "decision_time": CUTOFF,
        "component_feature_bundles": {
            "TEST": {
                name: {"status": "observed", "score": 75}
                for name in names
            }
        },
    }


def manifest():
    features = ("trend", "relative_strength", "wyckoff", "volume",
                "smc", "liquidity", "sector", "broker_flow")
    return {"TEST": {
        name: {"status": "verified", "source_id": "SRC-" + name,
               "evidence_id": "EV-" + name,
               "available_at": "2026-11-27T11:00:00+05:45"}
        for name in features
    }}


class StrategyIntegrationTests(unittest.TestCase):
    def test_existing_observed_features_adapt_to_each_strategy(self):
        result = adapt_feature_snapshot_to_strategy_evidence(
            feature_snapshot=snapshot(), evidence_manifest=manifest())
        symbol = result["symbols"]["TEST"]
        self.assertEqual(set(symbol), set(STRATEGIES))
        self.assertEqual(symbol["trend_momentum"]["feature_evidence"]["trend"]["score"], "75")
        self.assertEqual(symbol["broker_footprint"]["feature_evidence"]["broker_flow"]["feature_source"], "broker")

    def test_unimplemented_features_remain_missing(self):
        result = adapt_feature_snapshot_to_strategy_evidence(
            feature_snapshot=snapshot(), evidence_manifest=manifest())
        hybrid = result["symbols"]["TEST"]["hybrid_consensus"]
        self.assertIn("idpat_price_volume", hybrid["missing_features"])
        self.assertIn("accumulation_distribution", hybrid["missing_features"])
        self.assertIn("market_structure", hybrid["missing_features"])

    def test_experimental_smc_is_not_promoted(self):
        data = snapshot()
        data["component_feature_bundles"]["TEST"]["smc"]["status"] = "experimental_only"
        result = adapt_feature_snapshot_to_strategy_evidence(
            feature_snapshot=data, evidence_manifest=manifest())
        self.assertNotIn("smc", result["symbols"]["TEST"]["trend_momentum"]["feature_evidence"])

    def test_future_or_unverified_provenance_is_rejected(self):
        evidence = manifest()
        evidence["TEST"]["trend"]["available_at"] = "2026-11-27T13:00:00+05:45"
        evidence["TEST"]["wyckoff"]["status"] = "unverified"
        result = adapt_feature_snapshot_to_strategy_evidence(
            feature_snapshot=snapshot(), evidence_manifest=evidence)
        adapted = result["symbols"]["TEST"]["trend_momentum"]["feature_evidence"]
        self.assertNotIn("trend", adapted)
        self.assertNotIn("wyckoff", adapted)

    def test_missing_bundle_and_bad_cutoff_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "component_feature_bundles_required"):
            adapt_feature_snapshot_to_strategy_evidence(
                feature_snapshot={"decision_time": CUTOFF}, evidence_manifest={})
        with self.assertRaisesRegex(ValueError, "timezone_aware"):
            adapt_feature_snapshot_to_strategy_evidence(
                feature_snapshot=snapshot(), evidence_manifest=manifest(),
                decision_time="2026-11-27T12:00:00")


if __name__ == "__main__":
    unittest.main()

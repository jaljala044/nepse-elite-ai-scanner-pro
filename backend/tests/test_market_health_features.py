import unittest
from app.market_health_features import market_health_features

DIGEST = "a" * 64

def components(values, session="2026-11-25"):
    return {name: {"status": "verified", "score": score, "as_of_session": session,
                   "source_id": f"validated-{name}-v1", "source_payload_sha256": DIGEST}
            for name, score in values.items()}

class MarketHealthFeaturesTests(unittest.TestCase):
    def test_bull_requires_strong_trend_breadth_and_turnover(self):
        result = market_health_features(components({
            "trend": 80, "breadth": 75, "turnover": 70,
            "sector_participation": 65, "volatility": 60,
        }), decision_session="2026-11-25")
        self.assertEqual(result["regime"], "bull")
        self.assertEqual(result["trading_posture"], "trade_selectively_to_aggressively")
        self.assertEqual(result["coverage_pct"], 100)
        self.assertEqual(result["confidence"], "HIGH")

    def test_weak_breadth_prevents_bull_label(self):
        result = market_health_features(components({
            "trend": 85, "breadth": 30, "turnover": 80,
            "sector_participation": 70, "volatility": 50,
        }), decision_session="2026-11-25")
        self.assertNotEqual(result["regime"], "bull")

    def test_missing_component_is_not_imputed(self):
        result = market_health_features(components({
            "trend": 70, "breadth": 65, "turnover": 60,
        }), decision_session="2026-11-25")
        self.assertIsNone(result["component_scores"]["sector_participation"])
        self.assertEqual(result["coverage_pct"], 70)
        self.assertEqual(result["regime"], "unknown")
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("sector_participation", result["missing_components"])

    def test_stale_component_is_withheld(self):
        data = components({"trend": 70, "breadth": 65, "turnover": 60})
        data["breadth"]["as_of_session"] = "2026-11-24"
        result = market_health_features(data, decision_session="2026-11-25")
        self.assertIsNone(result["component_scores"]["breadth"])
        self.assertEqual(result["withheld_reasons"]["breadth"], "as_of_session_mismatch")

    def test_unverified_or_bad_provenance_is_withheld(self):
        data = components({"trend": 70, "breadth": 65, "turnover": 60})
        data["trend"]["status"] = "provisional"
        data["breadth"]["source_payload_sha256"] = "bad"
        result = market_health_features(data, decision_session="2026-11-25")
        self.assertIsNone(result["component_scores"]["trend"])
        self.assertIsNone(result["component_scores"]["breadth"])
        self.assertEqual(result["regime"], "unknown")

    def test_markdown_preserves_capital(self):
        result = market_health_features(components({
            "trend": 20, "breadth": 25, "turnover": 30,
            "sector_participation": 20, "volatility": 15,
        }), decision_session="2026-11-25")
        self.assertEqual(result["regime"], "markdown")
        self.assertEqual(result["trading_posture"], "preserve_capital")

    def test_invalid_scores_rejected(self):
        data = components({"trend": 120, "breadth": 65, "turnover": 60})
        with self.assertRaises(ValueError):
            market_health_features(data, decision_session="2026-11-25")

if __name__ == "__main__":
    unittest.main()

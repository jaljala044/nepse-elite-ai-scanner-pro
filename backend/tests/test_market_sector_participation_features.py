import unittest

from app.market_sector_participation_features import market_sector_participation_component

DIGEST = "d" * 64
SESSION = "2026-11-25"
WINDOWS = ("1W", "1M", "3M", "6M")


def provenance(source_id, **extra):
    return {
        "status": "verified", "source_id": source_id,
        "source_payload_sha256": DIGEST, "as_of_session": SESSION, **extra,
    }


def features(returns=None):
    returns = returns or {
        "Banking": (2.0, 2.0, 4.0, 4.0),
        "Hydropower": (1.0, 1.0, 3.0, 3.0),
        "Insurance": (-1.0, -1.0, 2.0, 2.0),
        "Hotels": (-2.0, -2.0, -1.0, -1.0),
        "Manufacturing": (0.5, 0.5, 1.0, 1.0),
    }
    sectors = {}
    for sector, values in returns.items():
        sectors[sector] = {"windows": {
            window: {"status": "observed", "median_return_pct": value}
            for window, value in zip(WINDOWS, values)
        }}
    return {
        "status": "observed", "as_of_session": SESSION,
        "method": "median_constituent_return_cross_sector_percentile",
        "sectors": sectors,
    }


class MarketSectorParticipationTests(unittest.TestCase):
    def run_component(self, sector_features=None, universe=None, prices=None):
        universe = universe or provenance("verified-sector-master", expected_sector_count=5)
        prices = prices or provenance("verified-equity-prices")
        return market_sector_participation_component(
            sector_features or features(), sector_universe_provenance=universe,
            price_evidence=prices, decision_session=SESSION,
        )

    def test_verified_four_horizon_sector_participation_component(self):
        result = self.run_component()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["score"], 70.0)
        for window, expected in (("1W", 60.0), ("1M", 60.0), ("3M", 80.0), ("6M", 80.0)):
            self.assertEqual(result["metrics"]["positive_sector_participation_pct"][window], expected)
        self.assertEqual(result["metrics"]["weights"], {"1W": 0.20, "1M": 0.30, "3M": 0.30, "6M": 0.20})

    def test_weights_use_distinct_horizon_participation(self):
        returns = {
            "A": (1, 1, 1, 1), "B": (1, 1, 1, 1),
            "C": (-1, 1, 1, 1), "D": (-1, -1, -1, 1),
            "E": (-1, -1, -1, -1),
        }
        result = self.run_component(sector_features=features(returns))
        self.assertEqual(result["score"], 60.0)
        self.assertEqual(result["metrics"]["positive_sector_participation_pct"]["1W"], 40.0)

    def test_weak_participation_warns(self):
        returns = {name: (-1.0, -1.0, -2.0, -3.0) for name in ("A", "B", "C", "D", "E")}
        result = self.run_component(sector_features=features(returns))
        self.assertEqual(result["score"], 0.0)
        self.assertIn("broad_sector_participation_weak", result["warnings"])

    def test_short_term_deterioration_is_flagged(self):
        returns = {
            "A": (1, 1, 2, 3), "B": (-1, 1, 2, 3),
            "C": (-1, 1, 2, 3), "D": (-1, 1, 2, 3), "E": (-1, 1, 2, 3),
        }
        result = self.run_component(sector_features=features(returns))
        self.assertIn("short_term_sector_participation_deteriorating", result["warnings"])

    def test_unverified_universe_withholds_score(self):
        universe = provenance("sector-master", expected_sector_count=5)
        universe["status"] = "provisional"
        self.assertIsNone(self.run_component(universe=universe)["score"])

    def test_stale_price_evidence_withholds_score(self):
        prices = provenance("prices")
        prices["as_of_session"] = "2026-11-24"
        self.assertIsNone(self.run_component(prices=prices)["score"])

    def test_sector_feature_session_mismatch_withholds_score(self):
        data = features()
        data["as_of_session"] = "2026-11-24"
        self.assertIsNone(self.run_component(sector_features=data)["score"])

    def test_missing_any_horizon_coverage_withholds_score(self):
        data = features()
        data["sectors"]["Hotels"]["windows"]["6M"]["status"] = "insufficient_evidence"
        data["sectors"]["Manufacturing"]["windows"]["6M"]["status"] = "insufficient_evidence"
        result = self.run_component(sector_features=data)
        self.assertEqual(result["reason"], "sector_return_coverage_below_threshold")
        self.assertIsNone(result["score"])
        self.assertEqual(result["coverage_pct"]["6M"], 60.0)

    def test_sector_count_mismatch_withholds_score(self):
        data = features()
        data["sectors"].pop("Hotels")
        result = self.run_component(sector_features=data)
        self.assertEqual(result["reason"], "sector_result_count_mismatch")

    def test_invalid_return_rejected(self):
        data = features()
        data["sectors"]["Banking"]["windows"]["1W"]["median_return_pct"] = float("nan")
        with self.assertRaises(ValueError):
            self.run_component(sector_features=data)


if __name__ == "__main__":
    unittest.main()

import unittest

from app.market_sector_participation_features import market_sector_participation_component

DIGEST = "d" * 64
SESSION = "2026-11-25"


def provenance(source_id, **extra):
    return {
        "status": "verified", "source_id": source_id,
        "source_payload_sha256": DIGEST, "as_of_session": SESSION, **extra,
    }


def features(returns=None):
    returns = returns or {
        "Banking": (2.0, 4.0),
        "Hydropower": (1.0, 3.0),
        "Insurance": (-1.0, 2.0),
        "Hotels": (-2.0, -1.0),
        "Manufacturing": (0.5, 1.0),
    }
    sectors = {}
    for sector, (one_month, three_month) in returns.items():
        sectors[sector] = {
            "windows": {
                "1M": {"status": "observed", "median_return_pct": one_month},
                "3M": {"status": "observed", "median_return_pct": three_month},
            }
        }
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

    def test_verified_sector_participation_component(self):
        result = self.run_component()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["score"], 68.0)
        self.assertEqual(result["metrics"]["positive_sector_participation_pct"]["1M"], 60.0)
        self.assertEqual(result["metrics"]["positive_sector_participation_pct"]["3M"], 80.0)

    def test_weak_participation_warns(self):
        returns = {name: (-1.0, -2.0) for name in ("A", "B", "C", "D", "E")}
        result = self.run_component(sector_features=features(returns))
        self.assertEqual(result["score"], 0.0)
        self.assertIn("broad_sector_participation_weak", result["warnings"])

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

    def test_sector_coverage_below_threshold_withholds_score(self):
        data = features()
        data["sectors"]["Hotels"]["windows"]["1M"]["status"] = "insufficient_evidence"
        data["sectors"]["Hotels"]["windows"]["3M"]["status"] = "insufficient_evidence"
        data["sectors"]["Manufacturing"]["windows"]["1M"]["status"] = "insufficient_evidence"
        data["sectors"]["Manufacturing"]["windows"]["3M"]["status"] = "insufficient_evidence"
        result = self.run_component(sector_features=data)
        self.assertEqual(result["reason"], "sector_return_coverage_below_threshold")
        self.assertIsNone(result["score"])

    def test_sector_count_mismatch_withholds_score(self):
        data = features()
        data["sectors"].pop("Hotels")
        result = self.run_component(sector_features=data)
        self.assertEqual(result["reason"], "sector_result_count_mismatch")

    def test_invalid_return_rejected(self):
        data = features()
        data["sectors"]["Banking"]["windows"]["1M"]["median_return_pct"] = float("nan")
        with self.assertRaises(ValueError):
            self.run_component(sector_features=data)


if __name__ == "__main__":
    unittest.main()

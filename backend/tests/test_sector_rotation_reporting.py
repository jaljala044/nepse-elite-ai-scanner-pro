import unittest

from app.sector_rotation_reporting import (
    adapt_verified_sector_rotation,
    sector_rotation_report,
)

SESSION = "2026-11-27"


def rotation():
    def detail(classification, score, rank, returns):
        return {
            "score_status": "observed",
            "classification": classification,
            "weighted_excess_return_pct": score,
            "relative_strength_rank_pct": rank,
            "membership_coverage_pct": 100.0,
            "windows": {
                key: {
                    "status": "observed",
                    "median_return_pct": value,
                    "median_excess_return_pct": value / 2,
                    "coverage_pct": 100.0,
                } for key, value in returns.items()
            },
        }
    return {
        "status": "observed", "mode": "descriptive_only",
        "as_of_session": SESSION, "sector_count": 2,
        "scored_sector_count": 2, "sector_coverage_pct": 100.0,
        "weights": {"1W": .2, "1M": .3, "3M": .3, "6M": .2},
        "sectors": {
            "BANK": detail("Leading", 12.5, 75, {"1W": 2, "1M": 4, "3M": 8, "6M": 10}),
            "HYDRO": detail("Lagging", -8, 25, {"1W": -1, "1M": -2, "3M": -4, "6M": -5}),
        },
    }


class SectorRotationReportingTests(unittest.TestCase):
    def test_rotation_adapts_to_market_health_schema(self):
        result = adapt_verified_sector_rotation(rotation(), decision_session=SESSION)
        self.assertEqual(result["method"], "median_constituent_return_cross_sector_percentile")
        self.assertEqual(result["sectors"]["BANK"]["windows"]["1W"]["median_return_pct"], 2)

    def test_report_ranks_sectors_and_preserves_classification(self):
        result = sector_rotation_report(rotation(), decision_session=SESSION)
        self.assertEqual([x["sector"] for x in result["ranked_sectors"]], ["BANK", "HYDRO"])
        self.assertEqual(result["ranked_sectors"][0]["classification"], "Leading")
        self.assertFalse(result["signals_enabled"])
        self.assertIsNone(result["probability"])

    def test_stale_rotation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "as_of_session_mismatch"):
            adapt_verified_sector_rotation(rotation(), decision_session="2026-11-28")

    def test_insufficient_rotation_is_rejected(self):
        data = rotation()
        data["status"] = "insufficient_evidence"
        with self.assertRaisesRegex(ValueError, "not_observed"):
            sector_rotation_report(data, decision_session=SESSION)

    def test_unscored_sector_label_is_withheld(self):
        data = rotation()
        data["sectors"]["HYDRO"]["score_status"] = "insufficient_evidence"
        result = sector_rotation_report(data, decision_session=SESSION)
        hydro = result["ranked_sectors"][1]
        self.assertEqual(hydro["classification"], "insufficient_evidence")
        self.assertIsNone(hydro["weighted_excess_return_pct"])

    def test_bad_coverage_rejected(self):
        data = rotation()
        data["sector_coverage_pct"] = 120
        with self.assertRaisesRegex(ValueError, "out_of_range"):
            sector_rotation_report(data, decision_session=SESSION)


if __name__ == "__main__":
    unittest.main()

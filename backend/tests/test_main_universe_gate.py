import unittest

from app import main


class MainUniverseGateTests(unittest.TestCase):
    def test_universe_endpoint_exposes_281_secondary_candidates_not_canonical(self):
        result = main.universe()
        self.assertEqual(result["record_count"], 281)
        self.assertFalse(result["membership_authoritatively_verified"])
        self.assertFalse(result["promotion_allowed"])

    def test_mutual_fund_is_rejected_before_analysis(self):
        result = main.scan(main.ScanRequest(symbols=["NICEF"]))
        item = result["results"][0]
        self.assertEqual(item["status"], "out_of_scope")
        self.assertFalse(item["eligibility"]["eligible"])
        self.assertEqual(item["signals"], [])
        self.assertEqual(item["metrics"], {})

    def test_unknown_symbol_is_rejected_before_analysis(self):
        result = main.scan(main.ScanRequest(symbols=["NOTREAL"]))
        self.assertEqual(result["results"][0]["status"], "out_of_scope")



    def test_market_health_endpoint_fails_closed_without_production_sources(self):
        result = main.market_health()
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["regime"], "unknown")
        self.assertEqual(result["trading_posture"], "preserve_capital")
        self.assertIsNone(result["market_health_score"])
        self.assertEqual(result["coverage_pct"], 0.0)
        self.assertEqual(result["action"], "PRESERVE_CAPITAL")
        self.assertFalse(result["readiness"]["production_source_store_connected"])
        self.assertEqual(
            set(result["missing_components"]),
            {"trend", "breadth", "turnover", "sector_participation", "volatility"},
        )

    def test_market_health_readiness_does_not_claim_authoritative_sector_membership(self):
        result = main.market_health()
        self.assertEqual(
            result["readiness"]["verified_sector_membership"],
            "not_authoritatively_verified",
        )
        self.assertIsNone(result["probability"])

    def test_scan_exposes_sector_registry_state_without_promoting_membership(self):
        result = main.scan(main.ScanRequest(symbols=["ADBL"]))
        item = result["results"][0]
        self.assertEqual(item["sector_evidence"]["status"], "not_configured")
        self.assertIsNone(item["sector_evidence"]["sector_code"])
        self.assertTrue(item["sector_evidence"]["research_only"])
        self.assertEqual(item["sector_evidence"]["score_adjustment"], 0)
        self.assertFalse(item["sector_evidence"]["recommendation_override"])

    def test_readiness_reports_sector_registry_not_configured(self):
        result = main.research_readiness()
        self.assertEqual(result["sector_evidence_registry"]["status"], "not_configured")
        self.assertFalse(result["sector_evidence_registry"]["verified"])
        self.assertFalse(result["sector_evidence_registry"]["admission_allowed"])

if __name__ == "__main__":
    unittest.main()

import unittest

from app.main import app, market_dashboard
from unittest.mock import patch


class Part2ResearchRouteTests(unittest.TestCase):
    def test_market_and_broker_research_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/v1/research/market-dashboard",
            "/v1/research/index-intelligence",
            "/v1/research/sector-rotation",
            "/v1/research/sector-confluence",
            "/v1/research/broker-dashboard",
            "/v1/research/broker-patterns",
            "/v1/research/early-signals",
        }
        self.assertTrue(expected.issubset(paths))


    def test_market_dashboard_without_deployment_artifacts_is_unavailable(self):
        with patch.dict("os.environ", {"NEPSE_MARKET_ARTIFACT_ROOT": "", "NEPSE_MARKET_ARTIFACT_REGISTRY": ""}):
            result = market_dashboard()
        self.assertEqual(result["mode"], "research_only")
        self.assertFalse(result["signals_enabled"])
        self.assertFalse(result["trade_actions_enabled"])
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(set(result["modules"]), {"market_health", "daily_market_participation", "sector_rotation", "index_rotation"})
        self.assertTrue(all(item["data"] is None for item in result["modules"].values()))


if __name__ == "__main__":
    unittest.main()

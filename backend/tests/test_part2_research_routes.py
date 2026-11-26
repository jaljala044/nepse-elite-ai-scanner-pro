import unittest

from app.main import app


class Part2ResearchRouteTests(unittest.TestCase):
    def test_market_and_broker_research_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/v1/research/index-intelligence",
            "/v1/research/sector-rotation",
            "/v1/research/sector-confluence",
            "/v1/research/broker-dashboard",
            "/v1/research/broker-patterns",
            "/v1/research/early-signals",
        }
        self.assertTrue(expected.issubset(paths))


if __name__ == "__main__":
    unittest.main()

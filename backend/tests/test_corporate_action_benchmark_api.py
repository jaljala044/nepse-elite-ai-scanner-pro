import unittest
from fastapi.testclient import TestClient
from app.main import app


class CorporateActionBenchmarkAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.payload = {
            "symbol": "TEST",
            "as_of_date": "2025-01-03",
            "evidence_cutoff": "2025-01-03T15:00:00+05:45",
            "ohlcv_rows": [
                {"date": "2025-01-01", "open": 100, "high": 110, "low": 90, "close": 100, "volume": 1000},
                {"date": "2025-01-02", "open": 50, "high": 55, "low": 45, "close": 50, "volume": 2000},
            ],
            "corporate_actions": [{
                "status": "verified", "source_id": "source-1",
                "available_at": "2025-01-01T10:00:00+05:45",
                "ex_date": "2025-01-02", "action_type": "bonus", "ratio": 1
            }],
            "portfolio_equity_curve": [
                {"date": "2025-01-01", "equity": 1000},
                {"date": "2025-01-02", "equity": 1100}
            ],
            "benchmark_symbol": "NEPSE",
            "benchmark_rows": [
                {"date": "2025-01-01", "close": 2000},
                {"date": "2025-01-02", "close": 2100}
            ]
        }

    def test_returns_adjusted_ohlcv_and_benchmark_excess(self):
        response = self.client.post("/v1/research/backtest/corporate-action-benchmark", json=self.payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["corporate_action_adjustment"]["rows"][0]["close"], 50)
        self.assertEqual(body["benchmark_comparison"]["excess_return_pct"], 0)
        self.assertFalse(body["production_eligible"])

    def test_lookahead_action_fails_closed(self):
        self.payload["corporate_actions"][0]["available_at"] = "2025-01-04T10:00:00+05:45"
        response = self.client.post("/v1/research/backtest/corporate-action-benchmark", json=self.payload)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

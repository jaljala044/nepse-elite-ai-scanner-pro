import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


class PortfolioBacktestAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_API_DATABASE"] = str(Path(self.tmp.name) / "portfolio.duckdb")
        self.client = TestClient(app)

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def test_unknown_signal_is_not_ignored(self):
        response = self.client.post("/v1/research/backtest/portfolio", json={
            "signal_ids": ["0" * 64], "evaluation_date": "2025-01-31",
            "portfolio_sessions": ["2025-01-30", "2025-01-31"],
            "portfolio_calendar_evidence": {},
            "verified_sessions_by_symbol": {}, "calendar_evidence_by_symbol": {},
            "sector_by_symbol": {}, "initial_capital": 100000,
            "cost_assumptions_by_symbol": {}, "execution_config_by_symbol": {}
        })
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

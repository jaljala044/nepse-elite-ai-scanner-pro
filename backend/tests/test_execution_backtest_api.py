import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


class ExecutionScenarioAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_API_DATABASE"] = str(Path(self.tmp.name) / "execution.duckdb")
        self.client = TestClient(app)

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def test_unknown_signal_is_not_simulated(self):
        response = self.client.post("/v1/research/backtest/execution-scenario", json={
            "signal_id": "0" * 64, "evaluation_date": "2025-01-31",
            "quantity": 10, "verified_sessions": ["2025-01-01"],
            "calendar_evidence": {"status": "verified", "source_id": "fixture",
                "coverage": "1", "available_at": "2025-01-31T23:00:00+05:45"},
            "cost_assumptions": {}, "execution_config": {}
        })
        self.assertEqual(response.status_code, 404)

    def test_duplicate_batch_signal_ids_rejected(self):
        response = self.client.post("/v1/research/backtest/execution-batch", json={
            "signal_ids": ["abc", "abc"], "evaluation_date": "2025-01-31",
            "quantity_by_signal": {}, "verified_sessions_by_symbol": {},
            "calendar_evidence_by_symbol": {}, "cost_assumptions_by_symbol": {},
            "execution_config_by_symbol": {}
        })
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

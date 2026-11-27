import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


class WalkForwardBacktestAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_API_DATABASE"] = str(Path(self.tmp.name) / "backtest.duckdb")
        self.client = TestClient(app)

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def test_unknown_signal_id_is_not_silently_ignored(self):
        response = self.client.post("/v1/research/backtest/walk-forward", json={
            "signal_ids": ["0" * 64],
            "evaluation_date": "2025-01-31",
            "verified_sessions_by_symbol": {"TEST": ["2025-01-01"]},
            "calendar_evidence_by_symbol": {"TEST": {
                "status": "verified", "source_id": "calendar-fixture",
                "coverage": "1", "available_at": "2025-01-31T23:59:00+05:45"}}
        })
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

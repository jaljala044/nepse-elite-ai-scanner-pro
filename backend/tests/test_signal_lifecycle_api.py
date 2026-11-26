import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


class SignalLifecycleAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_API_DATABASE"] = str(Path(self.tmp.name) / "api.duckdb")
        self.client = TestClient(app)

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def test_freeze_store_and_list_buy_as_research_only(self):
        payload = {
            "symbol":"TEST", "decision_time":"2025-01-02T12:00:00Z",
            "horizon":"swing", "action":"BUY", "methodology":"p4.41_v1",
            "evidence":[{"evidence_id":"source-row-1","available_at":"2025-01-02T11:00:00Z"}],
            "details":{"plan":{"entry":"100","stop":"95","targets":["110"]}},
        }
        response = self.client.post("/v1/research/signals", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["record"]["classification"], "research_only_not_execution")
        self.assertEqual(data["storage"]["status"], "stored")
        listed = self.client.get("/v1/research/signals?horizon=swing")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["signals"][0]["action"], "BUY")

    def test_future_evidence_rejected(self):
        payload = {
            "symbol":"TEST", "decision_time":"2025-01-02T12:00:00Z",
            "horizon":"swing", "action":"BUY", "methodology":"p4.41_v1",
            "evidence":[{"evidence_id":"late","available_at":"2025-01-03T11:00:00Z"}],
            "details":{},
        }
        response = self.client.post("/v1/research/signals", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_performance_is_explicitly_research_reference(self):
        response = self.client.get("/v1/research/performance")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["classification"],
                         "gross_price_reference_statistics_not_backtest")


if __name__ == "__main__":
    unittest.main()

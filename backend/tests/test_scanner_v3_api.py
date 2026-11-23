import unittest
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.storage import DATA


class ScannerV3ApiTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(DATA)
        DATA.clear()
        DATA["ABC"] = []
        start = date(2026, 1, 1)
        for i in range(60):
            close = 100 + i
            DATA["ABC"].append({
                "date": start + timedelta(days=i),
                "open": close - 0.5,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000 + i,
            })
        self.client = TestClient(app)

    def tearDown(self):
        DATA.clear()
        DATA.update(self.original)

    def test_v3_endpoint_returns_descriptive_metrics(self):
        response = self.client.post("/v3/scan", json={"symbols": ["ABC"]})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["engine"], "v3")
        self.assertEqual(body["results"][0]["status"], "ready")
        self.assertIn("sma50", body["results"][0]["metrics"])

    def test_as_of_filter_is_applied(self):
        response = self.client.post("/v3/scan", json={
            "symbols": ["ABC"], "as_of": "2026-01-30"
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["as_of"], "2026-01-30")
        self.assertEqual(result["observations"], 30)
        self.assertEqual(result["status"], "insufficient_data")

    def test_legacy_endpoint_remains_available(self):
        response = self.client.post("/v1/scan", json={"symbols": ["ABC"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "research_only")


if __name__ == "__main__":
    unittest.main()

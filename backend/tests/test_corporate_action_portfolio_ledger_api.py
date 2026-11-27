import unittest
from fastapi.testclient import TestClient
from app.main import app


class CorporateActionPortfolioLedgerAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.payload = {
            "holdings": {"AAA": {"quantity": 100, "average_cost": 100}},
            "cash": 1000,
            "as_of_date": "2025-01-31",
            "evidence_cutoff": "2025-02-01T15:00:00+05:45",
            "actions": [{
                "action_id": "div-1", "action_type": "dividend", "symbol": "AAA",
                "status": "verified", "source_id": "cdsc-1",
                "available_at": "2025-01-01T10:00:00+05:45",
                "entitlement_quantity": 100, "cash_per_share": 5,
                "payment_date": "2025-01-15"
            }]
        }

    def test_ledger_endpoint_applies_cash_and_preserves_research_classification(self):
        response = self.client.post("/v1/research/portfolio/corporate-actions/apply", json=self.payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["cash"], 1500)
        self.assertEqual(body["holdings"]["AAA"]["quantity"], 100)
        self.assertFalse(body["production_eligible"])

    def test_unverified_action_returns_422(self):
        self.payload["actions"][0]["status"] = "unverified"
        response = self.client.post("/v1/research/portfolio/corporate-actions/apply", json=self.payload)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

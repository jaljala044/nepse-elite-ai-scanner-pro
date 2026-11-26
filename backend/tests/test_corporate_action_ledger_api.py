import unittest
from fastapi.testclient import TestClient
from app.main import app


class CorporateActionLedgerAPITests(unittest.TestCase):
    def test_endpoint_replays_verified_bonus_entitlement(self):
        client = TestClient(app)
        payload = {
            "initial_cash": 500,
            "initial_holdings": [{"symbol": "AAA", "quantity": 4, "total_cost": 400}],
            "corporate_actions": [{
                "symbol": "AAA", "status": "verified", "source_id": "cdsc-1",
                "available_at": "2025-01-01T09:00:00+05:45",
                "ex_date": "2025-01-02", "action_type": "bonus", "ratio": 1,
                "record_date": "2025-01-02", "listing_date": "2025-01-03"
            }],
            "price_rows_by_symbol": {"AAA": [
                {"date": "2025-01-01", "close": 100},
                {"date": "2025-01-02", "close": 50},
                {"date": "2025-01-03", "close": 50}
            ]},
            "as_of_date": "2025-01-03",
            "evidence_cutoff": "2025-01-03T15:00:00+05:45"
        }
        response = client.post("/v1/research/backtest/corporate-action-ledger", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ending_holdings"][0]["quantity"], 8)
        self.assertFalse(response.json()["production_eligible"])

    def test_unverified_action_rejected(self):
        client = TestClient(app)
        payload = {
            "initial_cash": 0, "initial_holdings": [],
            "corporate_actions": [{
                "symbol": "AAA", "status": "unverified", "source_id": "src",
                "available_at": "2025-01-01T09:00:00+05:45",
                "ex_date": "2025-01-02", "action_type": "split", "ratio": 1,
                "effective_date": "2025-01-02"
            }],
            "price_rows_by_symbol": {"AAA": [
                {"date": "2025-01-01", "close": 100},
                {"date": "2025-01-02", "close": 50}
            ]},
            "as_of_date": "2025-01-02",
            "evidence_cutoff": "2025-01-02T15:00:00+05:45"
        }
        response = client.post("/v1/research/backtest/corporate-action-ledger", json=payload)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

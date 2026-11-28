import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app


class PortfolioRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "NEPSE_PRIVATE_DB": str(Path(self.tmp.name) / "accounts.sqlite3"),
            "NEPSE_PORTFOLIO_DB": str(Path(self.tmp.name) / "portfolio.sqlite3"),
            "NEPSE_PROXY_SECRET": "x" * 40,
        })
        self.env.start()
        self.client = TestClient(app)
        self.headers = {"x-nepse-proxy-secret": "x" * 40, "x-nepse-subject": "investor-1"}

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


    def test_holding_preferences_api_is_authenticated_scoped_and_validated(self):
        created = self.client.post(
            "/v1/portfolios", headers=self.headers, json={"name": "Preferences"}
        )
        self.assertEqual(created.status_code, 201)
        portfolio_id = created.json()["id"]
        tx = self.client.post(
            f"/v1/portfolios/{portfolio_id}/transactions",
            headers=self.headers,
            json={"symbol": "CFCL", "side": "BUY", "quantity": "2500",
                  "price": "593", "trade_date": "2026-01-01"},
        )
        self.assertEqual(tx.status_code, 201)

        saved = self.client.put(
            f"/v1/portfolios/{portfolio_id}/holding-preferences/cfcl",
            headers=self.headers,
            json={"investment_horizon": "one_to_three_months",
                  "risk_preference": "aggressive_growth"},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["symbol"], "CFCL")
        self.assertEqual(saved.json()["investment_horizon"], "one_to_three_months")

        listed = self.client.get(
            f"/v1/portfolios/{portfolio_id}/holding-preferences",
            headers=self.headers,
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["preferences"]), 1)

        invalid = self.client.put(
            f"/v1/portfolios/{portfolio_id}/holding-preferences/CFCL",
            headers=self.headers,
            json={"investment_horizon": "forever", "risk_preference": "balanced"},
        )
        self.assertEqual(invalid.status_code, 422)

        other_headers = {**self.headers, "x-nepse-subject": "investor-2"}
        isolated = self.client.get(
            f"/v1/portfolios/{portfolio_id}/holding-preferences",
            headers=other_headers,
        )
        self.assertEqual(isolated.status_code, 404)

    def test_holding_preferences_api_rejects_missing_position(self):
        created = self.client.post(
            "/v1/portfolios", headers=self.headers, json={"name": "Empty"}
        )
        portfolio_id = created.json()["id"]
        response = self.client.put(
            f"/v1/portfolios/{portfolio_id}/holding-preferences/CFCL",
            headers=self.headers,
            json={"investment_horizon": "long_term", "risk_preference": "balanced"},
        )
        self.assertEqual(response.status_code, 404)

    def test_holding_preferences_endpoints_require_authentication(self):
        response = self.client.get("/v1/portfolios/example/holding-preferences")
        self.assertEqual(response.status_code, 401)
        response = self.client.put(
            "/v1/portfolios/example/holding-preferences/CFCL",
            json={"investment_horizon": "long_term", "risk_preference": "balanced"},
        )
        self.assertEqual(response.status_code, 401)

    def test_authentication_required(self):
        response = self.client.get("/v1/portfolios")
        self.assertEqual(response.status_code, 401)

    def test_portfolio_crud_and_transaction_routes(self):
        created = self.client.post("/v1/portfolios", headers=self.headers,
                                   json={"name": "Long term"})
        self.assertEqual(created.status_code, 201)
        portfolio_id = created.json()["id"]
        self.assertEqual(self.client.get("/v1/portfolios", headers=self.headers).json()["portfolios"][0]["id"], portfolio_id)

        tx = self.client.post(f"/v1/portfolios/{portfolio_id}/transactions",
                              headers=self.headers,
                              json={"symbol": "CFCL", "side": "BUY", "quantity": "2500",
                                    "price": "593", "fees": "0", "trade_date": "2026-01-01",
                                    "idempotency_key": "buy-1"})
        self.assertEqual(tx.status_code, 201)
        positions = self.client.get(f"/v1/portfolios/{portfolio_id}/positions",
                                     headers=self.headers).json()
        self.assertEqual(positions["positions"][0]["cost_basis"], "1482500")
        self.assertIn("UNKNOWN", positions["valuation_note"].upper())

        renamed = self.client.patch(f"/v1/portfolios/{portfolio_id}",
                                    headers=self.headers, json={"name": "Retirement"})
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["name"], "Retirement")

        deleted = self.client.delete(f"/v1/portfolios/{portfolio_id}", headers=self.headers)
        self.assertEqual(deleted.status_code, 204)

    def test_compact_transaction_date_is_rejected_at_api_boundary(self):
        created = self.client.post("/v1/portfolios", headers=self.headers,
                                   json={"name": "Date validation"})
        portfolio_id = created.json()["id"]
        response = self.client.post(
            f"/v1/portfolios/{portfolio_id}/transactions",
            headers=self.headers,
            json={"symbol": "CFCL", "side": "BUY", "quantity": "1",
                  "price": "100", "fees": "0", "trade_date": "20260102"},
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_calendar_date_is_rejected_by_service(self):
        created = self.client.post("/v1/portfolios", headers=self.headers,
                                   json={"name": "Date validation"})
        portfolio_id = created.json()["id"]
        response = self.client.post(
            f"/v1/portfolios/{portfolio_id}/transactions",
            headers=self.headers,
            json={"symbol": "CFCL", "side": "BUY", "quantity": "1",
                  "price": "100", "fees": "0", "trade_date": "2026-02-30"},
        )
        self.assertEqual(response.status_code, 422)

    def test_cross_user_access_is_not_found(self):
        created = self.client.post("/v1/portfolios", headers=self.headers, json={"name": "Private"})
        portfolio_id = created.json()["id"]
        other = {"x-nepse-proxy-secret": "x" * 40, "x-nepse-subject": "investor-2"}
        self.assertEqual(self.client.get(f"/v1/portfolios/{portfolio_id}", headers=other).status_code, 404)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import main


class MarketWideScannerAPITests(unittest.TestCase):
    def test_unavailable_universe_fails_closed(self):
        with patch.object(main, "EQUITY_UNIVERSE", None):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan/market-wide", json={})
        self.assertEqual(response.status_code, 503)

    def test_rejects_symbols_outside_candidate_universe(self):
        with patch.object(main, "EQUITY_UNIVERSE", {"symbols": ["ADBL"]}):
            with TestClient(main.app) as client:
                response = client.post(
                    "/v1/scan/market-wide", json={"symbols": ["NABIL"]}
                )
        self.assertEqual(response.status_code, 422)
        self.assertIn("outside the candidate", response.json()["detail"])

    def test_rejects_duplicate_symbols(self):
        with patch.object(main, "EQUITY_UNIVERSE", {"symbols": ["ADBL"]}):
            with TestClient(main.app) as client:
                response = client.post(
                    "/v1/scan/market-wide", json={"symbols": ["ADBL", "ADBL"]}
                )
        self.assertEqual(response.status_code, 422)
        self.assertIn("Duplicate", response.json()["detail"])

    def test_empty_observation_set_is_explicit_and_never_ranked(self):
        with patch.object(main, "EQUITY_UNIVERSE", {"symbols": ["ADBL"]}), \
             patch.object(main, "DATA", {}):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan/market-wide", json={})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["scanner_id"], "3A.01")
        self.assertEqual(payload["candidate_universe_count"], 1)
        self.assertEqual(payload["symbols_without_ohlcv"], 1)
        self.assertEqual(payload["results"][0]["status"], "insufficient_data")
        self.assertFalse(payload["ranking_enabled"])
        self.assertFalse(payload["results"][0]["buy_list_eligible"])

    def test_default_as_of_excludes_future_dated_rows(self):
        rows = [
            {"date": date(2026, 1, 1), "open": 10, "high": 12,
             "low": 9, "close": 11, "volume": 100},
            {"date": date(2099, 1, 1), "open": 10, "high": 12,
             "low": 9, "close": 11, "volume": 100},
        ]
        seen = []
        def analyze(symbol, selected_rows):
            seen.extend(row["date"] for row in selected_rows)
            return {"status": "screened", "signals": [], "metrics": {}}

        with patch.object(main, "EQUITY_UNIVERSE", {"symbols": ["ADBL"]}), \\
             patch.object(main, "DATA", {"ADBL": rows}), \\
             patch.object(main, "REVIEWED_ROWS", {}), \\
             patch.object(main, "analyze", side_effect=analyze):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan/market-wide", json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(seen, [date(2026, 1, 1)])
        self.assertEqual(response.json()["as_of"], "2026-11-27")

    def test_unreviewed_rows_cannot_emit_signals_or_metrics(self):
        rows = [{"date": date(2026, 1, 1), "open": 10, "high": 12,
                 "low": 9, "close": 11, "volume": 100}]
        with patch.object(main, "EQUITY_UNIVERSE", {"symbols": ["ADBL"]}), \
             patch.object(main, "DATA", {"ADBL": rows}), \
             patch.object(main, "REVIEWED_ROWS", {}), \
             patch.object(main, "analyze", return_value={
                 "status": "screened", "signals": ["candidate"], "metrics": {"x": 1}
             }):
            with TestClient(main.app) as client:
                response = client.post(
                    "/v1/scan/market-wide",
                    json={"symbols": ["ADBL"], "as_of": "2026-01-01"},
                )
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["status"], "eligibility_unverified")
        self.assertEqual(result["result_bucket"], "unknown_results")
        self.assertFalse(result["eligibility"]["eligible"])
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["metrics"], {})
        self.assertFalse(result["ranking_eligible"])
        self.assertFalse(result["buy_list_eligible"])


if __name__ == "__main__":
    unittest.main()

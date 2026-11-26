import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import main


class GenericUnknownScanPolicyTests(unittest.TestCase):
    def test_candidate_with_no_validated_rows_is_unknown_not_no_trade(self):
        with patch.object(main, "DATA", {"ADBL": []}):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={"symbols": ["ADBL"]})
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["status"], "unknown_result")
        self.assertEqual(result["data_status"], "UNKNOWN")
        self.assertEqual(result["data_quality"], "LOW_CONFIDENCE")
        self.assertEqual(result["overall_rating"], "NOT_RATED")
        self.assertEqual(result["horizon_actions"], {
            "t_plus_2": "UNKNOWN", "swing": "UNKNOWN",
            "positional": "UNKNOWN", "investment": "UNKNOWN",
        })
        self.assertFalse(result["eligibility"]["eligible"])
        self.assertIn("no_rows", result["eligibility"]["reasons"])
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["metrics"], {})
        self.assertEqual(result["market_structure"]["status"], "unknown")
        self.assertIn("NO_TRADE requires verified", result["scan_note"])


    def test_unknowns_are_visible_but_never_ranked_or_buy_candidates(self):
        with patch.object(main, "DATA", {"ADBL": []}):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={
                    "symbols": ["UNL", "ADBL", "NICEF"]
                })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        by_symbol = {item["symbol"]: item for item in payload["results"]}
        self.assertEqual(set(item["symbol"] for item in payload["unknown_results"]), {"UNL", "ADBL"})
        self.assertEqual(payload["ranked_results"], [])
        self.assertEqual(payload["buy_candidates"], [])
        self.assertEqual(payload["out_of_scope_results"][0]["symbol"], "NICEF")
        for symbol in ("UNL", "ADBL"):
            self.assertEqual(by_symbol[symbol]["result_bucket"], "unknown_results")
            self.assertFalse(by_symbol[symbol]["ranking_eligible"])
            self.assertFalse(by_symbol[symbol]["buy_list_eligible"])
            self.assertEqual(by_symbol[symbol]["overall_rating"], "NOT_RATED")



if __name__ == "__main__":
    unittest.main()

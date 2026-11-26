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


if __name__ == "__main__":
    unittest.main()

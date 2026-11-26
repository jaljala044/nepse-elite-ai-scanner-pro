import unittest
from fastapi.testclient import TestClient
from app import main


class UnlUnknownScanPolicyTests(unittest.TestCase):
    def test_unl_is_reported_unknown_not_no_trade_or_excluded(self):
        with TestClient(main.app) as client:
            response = client.post("/v1/scan", json={"symbols": ["UNL"]})
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["symbol"], "UNL")
        self.assertEqual(result["status"], "unknown_result")
        self.assertEqual(result["result_bucket"], "unknown_results")
        self.assertFalse(result["ranking_eligible"])
        self.assertFalse(result["buy_list_eligible"])
        self.assertEqual(result["data_status"], "UNKNOWN")
        self.assertEqual(result["data_quality"], "LOW_CONFIDENCE")
        self.assertEqual(result["overall_rating"], "NOT_RATED")
        self.assertEqual(result["horizon_actions"], {
            "t_plus_2": "UNKNOWN", "swing": "UNKNOWN",
            "positional": "UNKNOWN", "investment": "UNKNOWN",
        })
        self.assertFalse(result["eligibility"]["eligible"])
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["metrics"], {})
        self.assertIn("complete_primary_floorsheet_coverage_not_verified",
                      result["eligibility"]["reasons"])
        self.assertIn("no-trade", result["scan_note"])


if __name__ == "__main__":
    unittest.main()

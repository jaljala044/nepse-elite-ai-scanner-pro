import unittest

from app import main


class MainUniverseGateTests(unittest.TestCase):
    def test_universe_endpoint_exposes_281_secondary_candidates_not_canonical(self):
        result = main.universe()
        self.assertEqual(result["record_count"], 281)
        self.assertFalse(result["membership_authoritatively_verified"])
        self.assertFalse(result["promotion_allowed"])

    def test_mutual_fund_is_rejected_before_analysis(self):
        result = main.scan(main.ScanRequest(symbols=["NICEF"]))
        item = result["results"][0]
        self.assertEqual(item["status"], "out_of_scope")
        self.assertFalse(item["eligibility"]["eligible"])
        self.assertEqual(item["signals"], [])
        self.assertEqual(item["metrics"], {})

    def test_unknown_symbol_is_rejected_before_analysis(self):
        result = main.scan(main.ScanRequest(symbols=["NOTREAL"]))
        self.assertEqual(result["results"][0]["status"], "out_of_scope")


if __name__ == "__main__":
    unittest.main()

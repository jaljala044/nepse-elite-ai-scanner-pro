import unittest
from datetime import date, timedelta

from app.idpat_method import CONCEPTS, evaluate_idpat_method


class IDPATMethodFrameworkTests(unittest.TestCase):
    def rows(self, count=25):
        return [
            {"date": date(2025, 1, 1) + timedelta(days=i),
             "open": 100 + i, "high": 102 + i, "low": 99 + i,
             "close": 101 + i, "volume": 100 + (200 if i == count - 1 else 0)}
            for i in range(count)
        ]

    def test_all_15_source_concepts_are_registered(self):
        self.assertEqual(len(CONCEPTS), 15)
        self.assertEqual([item[0] for item in CONCEPTS], list(range(1, 16)))

    def test_ineligible_is_fail_closed(self):
        result = evaluate_idpat_method(self.rows())
        self.assertEqual(result["status"], "eligibility_unverified")
        self.assertIsNone(result["score"])
        self.assertEqual(result["action"], "NO TRADE")
        self.assertTrue(all(x["status"] == "UNKNOWN" for x in result["concepts"]))

    def test_unsupported_terms_remain_unknown(self):
        result = evaluate_idpat_method(self.rows(), eligible=True)
        by_number = {x["number"]: x for x in result["concepts"]}
        for number in (4, 5, 6, 12, 15):
            self.assertEqual(by_number[number]["status"], "UNKNOWN")

    def test_no_idpat_score_or_action_is_emitted(self):
        result = evaluate_idpat_method(
            self.rows(), eligible=True,
            upstream={"wyckoff": {"status": "research_only"},
                      "market_structure": {"status": "screened"}},
        )
        self.assertIsNone(result["score"])
        self.assertEqual(result["action"], "NO TRADE")
        self.assertEqual(result["status"], "research_framework_only")

    def test_bad_ohlcv_blocks_all_concepts(self):
        rows = self.rows()
        rows[-1]["high"] = 1
        result = evaluate_idpat_method(rows, eligible=True)
        self.assertEqual(result["status"], "data_quality_failed")
        self.assertTrue(all(x["status"] == "UNKNOWN" for x in result["concepts"]))

    def test_missing_history_stays_unknown(self):
        result = evaluate_idpat_method(self.rows(10), eligible=True)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["score"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations
import unittest
from capture_nepse_conflict_ohlcv import analyze_history_payload


def conflict():
    return {
        "symbol": "BGWT", "date": "2025-07-28",
        "source_a": {"ohlcv": [940, 992, 933.4, 957.17, 14028]},
        "source_b": {"ohlcv": [940, 992, 933.4, 945, 14028]},
    }


class NepseConflictOhlcvCaptureTests(unittest.TestCase):
    def test_official_row_matching_source_a_is_detected(self):
        payload = {"content": [{
            "businessDate": "2025-07-28T00:00:00", "openPrice": 940,
            "highPrice": 992, "lowPrice": 933.4, "closePrice": 957.17,
            "totalTradedQuantity": 14028,
        }], "totalPages": 1}
        result = analyze_history_payload(payload, [conflict()])
        self.assertEqual(result["status"], "all_conflicts_have_primary_match")
        self.assertEqual(result["conflict_comparisons"][0]["status"], "matches_source_a")
        self.assertFalse(result["canonical_promotion_allowed"])
        self.assertTrue(result["decision_requires_review"])

    def test_official_row_matching_source_b_is_detected(self):
        payload = {"content": [{
            "businessDate": "2025-07-28", "openPrice": 940, "highPrice": 992,
            "lowPrice": 933.4, "closePrice": 945, "totalTradedQuantity": 14028,
        }]}
        result = analyze_history_payload(payload, [conflict()])
        self.assertEqual(result["conflict_comparisons"][0]["status"], "matches_source_b")

    def test_partial_primary_row_reports_missing_ohlcv_fields(self):
        payload = {"content": [{"date": "2025-07-28", "close": 945}]}
        result = analyze_history_payload(payload, [conflict()])
        self.assertEqual(result["conflict_comparisons"][0]["status"], "partial_primary_fields")
        self.assertEqual(result["conflict_comparisons"][0]["missing_fields"], ["open", "high", "low", "volume"])
        self.assertTrue(result["decision_requires_review"])

    def test_missing_primary_date_is_not_imputed(self):
        payload = {"content": [{
            "businessDate": "2025-07-29", "openPrice": 940, "highPrice": 992,
            "lowPrice": 933.4, "closePrice": 945, "totalTradedQuantity": 14028,
        }]}
        result = analyze_history_payload(payload, [conflict()])
        self.assertEqual(result["conflict_comparisons"][0]["status"], "no_primary_row")
        self.assertFalse(result["all_conflicts_have_primary_match"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from capture_nepse_market_summary_history import analyze_payload


class NepseMarketSummaryHistoryCaptureTests(unittest.TestCase):
    def test_primary_summary_dates_are_compared_without_promotion(self):
        payload = [
            {"businessDate": "2024-03-04T00:00:00", "totalTurnover": 100},
            {"businessDate": "2024-03-05", "totalTurnover": 200},
            {"businessDate": "2024-03-05", "totalTurnover": 200},
        ]
        result = analyze_payload(payload, {"2024-03-04", "2024-03-06"})
        self.assertEqual(result["date_field"], "businessDate")
        self.assertEqual(result["record_count"], 3)
        self.assertEqual(result["unique_date_count"], 2)
        self.assertEqual(result["duplicate_date_rows"], 1)
        self.assertEqual(result["date_comparison"]["candidate_dates_with_primary_summary"], 1)
        self.assertEqual(result["date_comparison"]["candidate_dates_without_primary_summary"], ["2024-03-06"])
        self.assertEqual(result["date_comparison"]["primary_summary_dates_outside_candidate_set"], ["2024-03-05"])
        self.assertFalse(result["canonical_calendar_promotion_allowed"])

    def test_non_list_payload_is_preserved_as_unknown_shape(self):
        result = analyze_payload({"error": "unauthorized"}, {"2024-03-04"})
        self.assertEqual(result["payload_type"], "dict")
        self.assertIsNone(result["date_field"])
        self.assertIsNone(result["date_comparison"])
        self.assertFalse(result["canonical_calendar_promotion_allowed"])

    def test_missing_or_invalid_dates_are_counted_not_inferred(self):
        payload = [
            {"businessDate": "2024-03-04"},
            {"businessDate": "not-a-date"},
            {"businessDate": None},
        ]
        result = analyze_payload(payload, {"2024-03-04", "2024-03-05"})
        self.assertEqual(result["date_record_count"], 1)
        self.assertEqual(result["invalid_date_row_count"], 2)
        self.assertEqual(result["date_comparison"]["candidate_dates_without_primary_summary"], ["2024-03-05"])
        self.assertFalse(result["canonical_calendar_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()

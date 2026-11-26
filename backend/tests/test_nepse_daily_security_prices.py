import unittest

from capture_nepse_daily_security_prices import analyze_daily_payload


class NepseDailySecurityPriceTests(unittest.TestCase):
    def test_unique_rows_for_requested_date_are_review_only(self):
        payload = {"content": [
            {"businessDate": "2026-11-19", "symbol": "ABC"},
            {"businessDate": "2026-11-19", "symbol": "XYZ"},
        ], "totalPages": 1, "totalElements": 2}
        result = analyze_daily_payload(payload, "2026-11-19")
        self.assertEqual(result["status"], "ROWS_RETURNED_REVIEW_ONLY")
        self.assertEqual(result["unique_symbol_count"], 2)

    def test_empty_rows_are_unknown_not_no_trade(self):
        self.assertEqual(analyze_daily_payload({"content": []}, "2026-11-19")["status"],
                         "UNKNOWN_NO_ROWS_NOT_ZERO_TRADE")

    def test_duplicate_symbol_and_wrong_date_are_exceptions(self):
        payload = {"content": [
            {"businessDate": "2026-11-19", "symbol": "ABC"},
            {"businessDate": "2026-11-19", "symbol": "ABC"},
            {"businessDate": "2026-11-20", "symbol": "XYZ"},
        ]}
        result = analyze_daily_payload(payload, "2026-11-19")
        self.assertEqual(result["status"], "REVIEW_EXCEPTIONS")
        self.assertEqual(result["duplicate_symbols"], ["ABC"])
        self.assertEqual(len(result["out_of_range_rows"]), 1)

    def test_pagination_incomplete_is_flagged(self):
        payload = {"content": [{"businessDate": "2026-11-19", "symbol": "ABC"}],
                   "totalPages": 2, "totalElements": 501}
        result = analyze_daily_payload(payload, "2026-11-19")
        self.assertTrue(result["pagination_incomplete"])
        self.assertEqual(result["status"], "REVIEW_EXCEPTIONS")

    def test_nested_page_shape_is_supported(self):
        payload = {"securityDailyTradeStatVos": {"content": [
            {"businessDate": "2026-11-19", "symbol": "ABC"}
        ], "totalPages": 1, "totalElements": 1}}
        self.assertEqual(analyze_daily_payload(payload, "2026-11-19")["status"],
                         "ROWS_RETURNED_REVIEW_ONLY")


if __name__ == "__main__":
    unittest.main()

import unittest

from capture_nepse_security_history import extract_history_payload


class NepseSecurityHistoryCaptureTests(unittest.TestCase):
    def test_valid_history_rows_are_preserved_in_requested_window(self):
        payload = {"totalPages": 1, "totalElements": 2, "content": [
            {"businessDate": "2026-11-19", "totalTrades": 10,
             "totalTradedQuantity": 100, "totalTradedValue": 10000},
            {"businessDate": "2026-11-20", "totalTrades": 12,
             "totalTradedQuantity": 120, "totalTradedValue": 12000},
        ]}
        result = extract_history_payload(payload, "2026-11-19", "2026-11-24")
        self.assertEqual(result["status"], "ROWS_RETURNED_REVIEW_ONLY")
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["rows"][0]["business_date"], "2026-11-19")

    def test_empty_history_is_unknown_not_no_trade(self):
        result = extract_history_payload({"totalPages": 1, "totalElements": 0, "content": []},
                                         "2026-11-19", "2026-11-24")
        self.assertEqual(result["status"], "UNKNOWN_NO_ROWS_NOT_ZERO_TRADE")

    def test_multiple_pages_are_incomplete(self):
        result = extract_history_payload({"totalPages": 2, "totalElements": 501, "content": []},
                                         "2026-11-19", "2026-11-24")
        self.assertEqual(result["status"], "PAGINATION_INCOMPLETE")

    def test_total_elements_exceeding_content_is_incomplete(self):
        result = extract_history_payload({"totalPages": 1, "totalElements": 2, "content": [
            {"businessDate": "2026-11-19", "totalTrades": 1,
             "totalTradedQuantity": 1, "totalTradedValue": 100},
        ]}, "2026-11-19", "2026-11-24")
        self.assertEqual(result["status"], "PAGINATION_INCOMPLETE")

    def test_duplicate_or_out_of_range_dates_fail_closed(self):
        duplicate = {"totalPages": 1, "content": [
            {"businessDate": "2026-11-19"},
            {"businessDate": "2026-11-19"},
        ]}
        self.assertEqual(extract_history_payload(duplicate, "2026-11-19", "2026-11-24")["status"],
                         "DUPLICATE_DATE_ROW")
        outside = {"totalPages": 1, "content": [{"businessDate": "2026-11-25"}]}
        self.assertEqual(extract_history_payload(outside, "2026-11-19", "2026-11-24")["status"],
                         "OUT_OF_RANGE_ROW")

    def test_unknown_payload_shape_is_not_empty_trade(self):
        self.assertEqual(extract_history_payload({"error": "denied"}, "2026-11-19", "2026-11-24")["status"],
                         "UNKNOWN_SCHEMA")


if __name__ == "__main__":
    unittest.main()

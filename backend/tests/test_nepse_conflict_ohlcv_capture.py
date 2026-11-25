from __future__ import annotations
import unittest
from capture_nepse_conflict_ohlcv import analyze_history_payload, request_date_specific_price_volume, request_today_price_without_host_header


def conflict():
    return {
        "symbol": "BGWT", "date": "2025-07-28",
        "source_a": {"ohlcv": [940, 992, 933.4, 957.17, 14028]},
        "source_b": {"ohlcv": [940, 992, 933.4, 945, 14028]},
    }


class NepseConflictOhlcvCaptureTests(unittest.TestCase):

    def test_historical_filter_keeps_current_session_payload_id(self):
        class FakeClient:
            def __init__(self):
                self.payload_date = None
                self.request_url = None

            def getPOSTPayloadIDForFloorSheet(self, business_date=None):
                self.payload_date = business_date
                return 123456

            def requestPOSTAPI(self, url, payload_generator):
                self.request_url = url
                return {"payload_id": payload_generator()}

        client = FakeClient()
        result = request_date_specific_price_volume(
            client, "/api/nots/market/today-price", "2025-07-28"
        )
        self.assertEqual(client.request_url, "/api/nots/market/today-price?size=500&businessDate=2025-07-28")
        self.assertIsNone(client.payload_date)
        self.assertEqual(result, {"payload_id": 123456})


    def test_today_price_probe_omits_explicit_host_header(self):
        class FakeHTTP:
            def __init__(self):
                self.kwargs = None

            def post(self, url, **kwargs):
                self.kwargs = {"url": url, **kwargs}
                return "response"

        class FakeClient:
            def __init__(self):
                self.client = FakeHTTP()

            def getAuthorizationHeaders(self):
                return {
                    "Authorization": "Salter test-token",
                    "Host": "nepalstock.com.np",
                    "Content-Type": "application/json",
                }

            def get_full_url(self, url):
                return "https://nepalstock.com.np" + url

            def getPOSTPayloadIDForFloorSheet(self):
                return 123456

        client = FakeClient()
        result = request_today_price_without_host_header(client, "/api/nots/nepse-data/today-price")
        self.assertEqual(result, "response")
        self.assertNotIn("Host", client.client.kwargs["headers"])
        self.assertEqual(client.client.kwargs["headers"]["Authorization"], "Salter test-token")
        self.assertEqual(client.client.kwargs["json"], {"id": 123456})

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

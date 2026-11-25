from __future__ import annotations
import unittest
import httpx
import os
import tempfile
from datetime import date, datetime
from zoneinfo import ZoneInfo
from capture_nepse_conflict_ohlcv import analyze_history_payload, request_date_specific_price_volume, request_today_price_without_host_header, request_today_price_with_browser_headers, configure_nepse_timezone, parse_legacy_todaysprice_html, parse_legacy_floor_html, fetch_official_company_floorsheet


def conflict():
    return {
        "symbol": "BGWT", "date": "2025-07-28",
        "source_a": {"ohlcv": [940, 992, 933.4, 957.17, 14028]},
        "source_b": {"ohlcv": [940, 992, 933.4, 945, 14028]},
    }


class NepseConflictOhlcvCaptureTests(unittest.TestCase):





    def test_official_company_floorsheet_aggregates_api_records(self):
        class FakeClient:
            def getFloorSheetOf(self, symbol, business_date, size):
                self.args = (symbol, business_date, size)
                return [
                    {"contractId": "2025072801000064", "contractQuantity": 10, "contractRate": 940, "contractAmount": 9400},
                    {"contractId": "2025072801000065", "contractQuantity": 20, "contractRate": 960, "contractAmount": 19200},
                ]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = fetch_official_company_floorsheet(
                FakeClient(), "BGWT", "2025-07-28", temp_dir
            )
            self.assertEqual(result["status"], "captured")
            self.assertEqual(result["record_count"], 2)
            self.assertEqual(result["open_from_first_contract"], 940)
            self.assertEqual(result["high"], 960)
            self.assertEqual(result["low"], 940)
            self.assertEqual(result["volume"], 30)
            self.assertAlmostEqual(result["full_day_vwap"], 953.333333, places=5)
            self.assertTrue(os.path.exists(result["response_path"]))

    def test_legacy_nepse_floor_parser_aggregates_trade_rows(self):
        html = """
        <table>
          <tr><th>S.No</th><th>Contract</th><th>Symbol</th><th>Buyer</th><th>Seller</th><th>Qty</th><th>Rate</th><th>Amount</th></tr>
          <tr><td>1</td><td>2025072801000064</td><td>BGWT</td><td>58</td><td>17</td><td>10</td><td>940</td><td>9400</td></tr>
          <tr><td>2</td><td>2025072801000065</td><td>BGWT</td><td>58</td><td>17</td><td>20</td><td>960</td><td>19200</td></tr>
          <tr><td>1/1</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
        </table>
        """
        result = parse_legacy_floor_html(html, "2025-07-28")
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual(result["open_from_first_contract"], 940)
        self.assertEqual(result["high"], 960)
        self.assertEqual(result["low"], 940)
        self.assertEqual(result["volume"], 30)
        self.assertAlmostEqual(result["full_day_vwap"], 953.333333, places=5)

    def test_legacy_nepse_table_parser_extracts_official_daily_fields(self):
        cells = ["x"] * 13 + ["145", "992.0", "933.4", "957.17", "14028", "12345678", "940.0"]
        html = "<table><tr>" + "".join(f"<td>{value}</td>" for value in cells) + "</tr></table>"
        result = parse_legacy_todaysprice_html(html)
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["fields"]["max_price"], 992.0)
        self.assertEqual(result["fields"]["min_price"], 933.4)
        self.assertEqual(result["fields"]["closing_price"], 957.17)
        self.assertEqual(result["fields"]["traded_shares"], 14028.0)

    def test_nepse_timezone_uses_kathmandu_local_date(self):
        configure_nepse_timezone()
        self.assertEqual(os.environ.get("TZ"), "Asia/Kathmandu")
        self.assertEqual(
            date.today(),
            datetime.now(ZoneInfo("Asia/Kathmandu")).date(),
        )

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


    def test_clean_browser_probe_uses_token_payload_without_host_header(self):
        class FakeResponse:
            status_code = 200

        class FakeClient:
            base_url = "https://www.nepalstock.com"

            def getAuthorizationHeaders(self):
                return {"Authorization": "Salter test-token", "Host": "www.nepalstock.com"}

            def getPOSTPayloadIDForFloorSheet(self):
                return 123456

            def get_full_url(self, url):
                return self.base_url + url

        seen = {}

        class FakeHTTP:
            def __init__(self, **kwargs):
                seen["http2"] = kwargs["http2"]
                seen["verify"] = kwargs["verify"]
                seen["hook"] = kwargs["event_hooks"]["response"][0]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, url, **kwargs):
                seen["url"] = url
                seen["headers"] = kwargs["headers"]
                seen["json"] = kwargs["json"]
                return FakeResponse()

        original = httpx.Client
        try:
            httpx.Client = FakeHTTP
            hook = lambda response: None
            result = request_today_price_with_browser_headers(
                FakeClient(), "/api/nots/nepse-data/today-price", hook
            )
        finally:
            httpx.Client = original

        self.assertEqual(result.status_code, 200)
        self.assertFalse(seen["http2"])
        self.assertNotIn("Host", seen["headers"])
        self.assertEqual(seen["headers"]["Authorization"], "Salter test-token")
        self.assertEqual(seen["json"], {"id": 123456})
        self.assertEqual(seen["hook"], hook)

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

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from capture_nepse_market_summary_history import analyze_payload, capture, main


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


    def test_only_unique_rows_with_positive_official_activity_metrics_are_confirmed(self):
        payload = [
            {"businessDate": "2026-11-24", "totalTurnover": 1000, "totalTradedShares": 500,
             "totalTransactions": 20, "tradedScrips": 12},
            {"businessDate": "2026-11-25", "totalTurnover": 0, "totalTradedShares": 0,
             "totalTransactions": 0, "tradedScrips": 0},
            {"businessDate": "2026-11-26", "totalTurnover": 100, "totalTradedShares": 10,
             "totalTransactions": 1, "tradedScrips": 1},
        ]
        result = analyze_payload(payload, {"2026-11-24", "2026-11-25", "2026-11-26"})
        self.assertEqual(result["activity_confirmed_dates"], ["2026-11-24", "2026-11-26"])
        self.assertEqual(result["activity_confirmed_date_count"], 2)
        self.assertEqual(result["activity_unverified_rows"][0]["date"], "2026-11-25")
        self.assertEqual(result["date_comparison"]["candidate_dates_with_validated_activity"],
                         ["2026-11-24", "2026-11-26"])
        self.assertFalse(result["canonical_calendar_promotion_allowed"])

    def test_duplicate_summary_dates_are_not_activity_confirmed(self):
        row = {"businessDate": "2026-11-24", "totalTurnover": 1000, "totalTradedShares": 500,
               "totalTransactions": 20, "tradedScrips": 12}
        result = analyze_payload([row, dict(row)], {"2026-11-24"})
        self.assertEqual(result["activity_confirmed_dates"], [])
        self.assertEqual(result["activity_duplicate_dates"], ["2026-11-24"])
        self.assertEqual(result["date_comparison"]["candidate_dates_without_validated_activity"],
                         ["2026-11-24"])

    def test_missing_activity_metrics_do_not_confirm_session(self):
        result = analyze_payload(
            [{"businessDate": "2026-11-24", "totalTurnover": 1000}],
            {"2026-11-24"},
        )
        self.assertEqual(result["activity_confirmed_date_count"], 0)
        self.assertEqual(result["activity_unverified_rows"][0]["fields"],
                         ["total_traded_shares", "total_transactions", "traded_scrips"])

    def test_capture_preserves_request_errors_in_top_level_report(self):
        class OfflineClient:
            def __init__(self, timeout):
                self.headers = {}
                self.client = SimpleNamespace(event_hooks={"response": []})

            def requestGETAPI(self, path):
                raise RuntimeError("fixture network failure")

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"nepse_client": SimpleNamespace(NepseClient=OfflineClient)}):
                report = capture(Path(tmp))
        self.assertIsNone(report["http_status"])
        self.assertEqual(len(report["request_errors"]), 2)
        self.assertEqual(report["request_errors"][0]["type"], "RuntimeError")

    def test_capture_keeps_raw_success_and_reports_date_analysis(self):
        body = b'[{"businessDate":"2026-11-25","totalTurnover":100}]'

        class Response:
            url = "https://nepalstock.com.np/api/nots/market-summary-history"
            status_code = 200
            content = body
            headers = {"date": "Wed, 26 Nov 2026 00:00:00 GMT", "content-type": "application/json"}

            def read(self):
                return self.content

        class OnlineClient:
            def __init__(self, timeout):
                self.headers = {}
                self.client = SimpleNamespace(event_hooks={"response": []})

            def requestGETAPI(self, path):
                response = Response()
                for hook in self.client.event_hooks["response"]:
                    hook(response)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch.dict(sys.modules, {"nepse_client": SimpleNamespace(NepseClient=OnlineClient)}):
                with patch.object(sys, "argv", ["capture", "--output-dir", tmp]):
                    with redirect_stdout(output):
                        exit_code = main()
            report = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(report["response_preserved"])
            self.assertEqual(report["payload_analysis"]["unique_date_count"], 1)
            self.assertEqual(report["request_errors"], [])
            self.assertEqual((Path(tmp) / "response-body.bin").read_bytes(), body)

    def test_http_200_from_non_nepse_origin_is_not_accepted_as_official(self):
        body = b'[{"businessDate":"2026-11-25","totalTurnover":100}]'

        class Response:
            url = "https://example.invalid/api/nots/market-summary-history"
            status_code = 200
            content = body
            headers = {"content-type": "application/json"}

            def read(self):
                return self.content

        class UntrustedOriginClient:
            def __init__(self, timeout):
                self.headers = {}
                self.client = SimpleNamespace(event_hooks={"response": []})

            def requestGETAPI(self, path):
                response = Response()
                for hook in self.client.event_hooks["response"]:
                    hook(response)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"nepse_client": SimpleNamespace(NepseClient=UntrustedOriginClient)}):
                report = capture(Path(tmp))
        self.assertIsNone(report["selected_attempt_number"])
        self.assertFalse(report["response_origin_verified"])
        self.assertFalse(report["response_preserved"])
        self.assertFalse(report["attempts"][0]["response_origin_verified"])

    def test_non_list_payload_is_preserved_as_unknown_shape(self):
        result = analyze_payload({"error": "unauthorized"}, {"2024-03-04"})
        self.assertEqual(result["payload_type"], "dict")
        self.assertIsNone(result["date_field"])
        self.assertIsNone(result["date_comparison"])
        self.assertFalse(result["canonical_calendar_promotion_allowed"])


    def test_list_without_date_field_keeps_all_rows_unverified(self):
        result = analyze_payload(
            [{"totalTurnover": 100, "totalTradedShares": 10,
              "totalTransactions": 1, "tradedScrips": 1}],
            {"2026-11-24"},
        )
        self.assertIsNone(result["date_field"])
        self.assertEqual(result["activity_confirmed_dates"], [])
        self.assertEqual(result["activity_unverified_rows"][0]["reason"],
                         "no_recognized_date_field")
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

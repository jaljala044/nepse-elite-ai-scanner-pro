from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from capture_nepse_market_summary_history import analyze_payload, capture


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
            with patch.dict(sys.modules, {"nepse_client": SimpleNamespace(NepseClient=OnlineClient)}):
                report = capture(Path(tmp))
            self.assertTrue(report["response_preserved"])
            self.assertEqual(report["payload_analysis"]["unique_date_count"], 1)
            self.assertEqual((Path(tmp) / "response-body.bin").read_bytes(), body)
            self.assertEqual(report["request_errors"], [])

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

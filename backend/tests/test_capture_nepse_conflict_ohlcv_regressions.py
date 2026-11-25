"""Regression tests for NEPSE conflict response classification."""
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "capture_nepse_conflict_ohlcv.py"
SPEC = importlib.util.spec_from_file_location("capture_nepse_conflict_ohlcv", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def conflict(day="2025-07-28"):
    return {
        "symbol": "BGWT",
        "date": day,
        "source_a": {"ohlcv": [940, 992, 933.4, 957.17, 14028]},
        "source_b": {"ohlcv": [940, 992, 933.4, 945, 14028]},
    }


class AnalyzeHistoryPayloadTests(unittest.TestCase):
    def test_query_window_expands_single_date_by_30_calendar_days(self):
        start, end = MODULE._query_window([conflict("2025-07-28")])
        self.assertEqual(start.isoformat(), "2025-06-28")
        self.assertEqual(end.isoformat(), "2025-08-27")

    def test_query_window_covers_multiple_conflict_dates(self):
        start, end = MODULE._query_window([conflict("2025-07-28"), conflict("2025-08-10")])
        self.assertEqual(start.isoformat(), "2025-06-28")
        self.assertEqual(end.isoformat(), "2025-09-09")

    def test_empty_content_is_valid_empty_response_and_emits_missing_comparison(self):
        result = MODULE.analyze_history_payload({"content": [], "totalElements": 0}, [conflict()])
        self.assertEqual(result["status"], "empty_valid_response")
        self.assertEqual(result["conflict_comparisons"][0]["status"], "no_primary_row")
        self.assertEqual(result["conflict_comparisons"][0]["date"], "2025-07-28")

    def test_empty_nested_content_is_not_misclassified_as_unknown_schema(self):
        result = MODULE.analyze_history_payload({"data": {"content": []}}, [conflict()])
        self.assertEqual(result["status"], "empty_valid_response")
        self.assertEqual(result["pagination"]["container"], "data.content")

    def test_nonempty_unrecognized_date_schema_is_distinct_from_empty(self):
        result = MODULE.analyze_history_payload({"content": [{"tradeDay": "2025-07-28"}]}, [conflict()])
        self.assertEqual(result["status"], "unmapped_schema")
        self.assertEqual(result["conflict_comparisons"][0]["status"], "unmapped_date_schema")

    def test_date_specific_board_row_matches_source_b_by_symbol(self):
        payload = {"content": [{
            "symbol": "BGWT", "openPrice": 940, "highPrice": 992,
            "lowPrice": 933.4, "closePrice": 945, "totalTradedQuantity": 14028,
        }], "totalElements": 1}
        result = MODULE.analyze_date_price_volume_payload(payload, [conflict()])
        self.assertEqual(result[0]["status"], "matches_source_b")
        self.assertEqual(result[0]["official_ohlcv"], ["940", "992", "933.4", "945", "14028"])

    def test_date_specific_board_row_missing_open_stays_partial(self):
        payload = {"content": [{
            "symbol": "BGWT", "highPrice": 992, "lowPrice": 933.4,
            "closePrice": 945, "totalTradedQuantity": 14028,
        }]}
        result = MODULE.analyze_date_price_volume_payload(payload, [conflict()])
        self.assertEqual(result[0]["status"], "partial_primary_fields")
        self.assertEqual(result[0]["missing_fields"], ["open"])

    def test_date_specific_board_empty_response_is_not_a_match(self):
        result = MODULE.analyze_date_price_volume_payload({"content": [], "totalElements": 0}, [conflict()])
        self.assertEqual(result[0]["status"], "no_primary_row")

    def test_date_specific_board_can_resolve_symbol_by_security_id(self):
        payload = {"content": [{
            "securityId": 9214, "openPrice": 940, "highPrice": 992,
            "lowPrice": 933.4, "closePrice": 945, "totalTradedQuantity": 14028,
        }]}
        result = MODULE.analyze_date_price_volume_payload(payload, [conflict()], {"9214": "BGWT"})
        self.assertEqual(result[0]["status"], "matches_source_b")

    def test_missing_open_is_reported_as_partial_primary_fields(self):
        row = {
            "businessDate": "2026-11-19",
            "highPrice": 334.2,
            "lowPrice": 330.0,
            "closePrice": 331.8,
            "totalTradedQuantity": 105340,
        }
        result = MODULE.analyze_history_payload({"content": [row]}, [conflict("2026-11-19")])
        comparison = result["conflict_comparisons"][0]
        self.assertEqual(comparison["status"], "partial_primary_fields")
        self.assertEqual(comparison["missing_fields"], ["open"])
        self.assertEqual(comparison["available_primary_fields"]["close"], "331.8")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from app.scenario_validation import validate_binary_forecasts
from app.walk_forward_report import build_walk_forward_report
from app.quarantine_guard import filter_quarantined_feature_rows


class QuarantineEndToEndAcceptanceTests(unittest.TestCase):
    def test_feature_filter_removes_full_symbol_span_and_preserves_other_symbols(self):
        rows = [
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2026-01-01","close":10},
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2026-01-03","close":12},
            {"record_type":"broker","symbol":"AAA","trade_date":"2026-01-03","amount":100},
            {"record_type":"ohlcv","symbol":"BBB","session_date":"2026-01-03","close":20},
        ]
        result = filter_quarantined_feature_rows(rows, {("AAA","2026-01-02")})
        self.assertEqual([(r["symbol"],r["record_type"]) for r in result], [("BBB","ohlcv")])

    def test_forecast_requires_server_pinned_ledger_when_configured_mandatory(self):
        with patch("app.scenario_validation.runtime_quarantine_keys",
                   side_effect=ValueError("pinned quarantine ledger required")):
            with self.assertRaisesRegex(ValueError, "pinned quarantine ledger required"):
                validate_binary_forecasts([1], [0.8], require_ledger=True)

    def test_forecast_with_valid_lineage_remains_descriptive(self):
        lineage = [{"symbol":"AAA","constituent_sessions":["2026-01-01","2026-01-02"]}]
        with patch("app.scenario_validation.runtime_quarantine_keys", return_value=frozenset()):
            result = validate_binary_forecasts([1], [0.8], lineage=lineage, require_ledger=True)
        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["sample_count"], 1)

    def test_walk_forward_requires_lineage_with_runtime_ledger(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8},
            {"observation_date":"2026-01-02","actual":0,"probability":0.2},
        ]
        with patch("app.walk_forward_report.runtime_quarantine_keys", return_value=frozenset()):
            with self.assertRaisesRegex(ValueError, "missing forecast constituent-session lineage"):
                build_walk_forward_report(rows, 1, 1, require_ledger=True)

    def test_walk_forward_accepts_unaffected_lineage(self):
        rows = [
            {"observation_date":"2026-01-01","actual":1,"probability":0.8,
             "symbol":"AAA","constituent_sessions":["2026-01-01"]},
            {"observation_date":"2026-01-02","actual":0,"probability":0.2,
             "symbol":"BBB","constituent_sessions":["2026-01-02"]},
        ]
        with patch("app.walk_forward_report.runtime_quarantine_keys", return_value=frozenset()):
            result = build_walk_forward_report(rows, 1, 1, require_ledger=True)
        self.assertEqual(result["fold_count"], 1)


if __name__ == "__main__":
    unittest.main()

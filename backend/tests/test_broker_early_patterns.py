import unittest

from app.broker_early_patterns import evaluate_broker_early_pattern


class BrokerEarlyPatternTests(unittest.TestCase):
    def setUp(self):
        self.windows = {}
        for horizon, count, flow in (
            ("1D", 1, "net_buyer"),
            ("1W", 5, "net_buyer"),
            ("1M", 21, "net_buyer"),
        ):
            self.windows[horizon] = {
                "status": "observed",
                "window_complete": True,
                "coded_amount_coverage_pct": 100,
                "execution_channels": [{
                    "execution_channel_code": "11",
                    "identity_status": "execution_channel_only",
                    "flow_class": flow,
                    "buy_amount": "1000",
                    "sell_amount": "100",
                    "net_amount": "900",
                    "gross_participation_pct": 12.5,
                    "active_sessions": count,
                    "prior_20_session_count": 20,
                    "latest_buy_vs_prior_20_avg_ratio": 2.0,
                    "latest_sell_vs_prior_20_avg_ratio": 0.5,
                }],
            }
        self.context = {
            "status": "verified",
            "symbol": "NABIL",
            "as_of_session": "2026-11-26",
            "available_at": "2026-11-26T15:00:00+05:45",
            "source_id": "verified-nepse-context",
            "source_payload_sha256": "a" * 64,
            "price_extension_status": "not_extended",
            "component_statuses": {
                "price": "verified",
                "nepse_index": "verified",
                "sector_index": "verified",
                "market_breadth": "verified",
                "turnover_liquidity": "verified",
                "circuit_context": "verified",
                "corporate_actions": "verified",
            },
        }

    def evaluate(self, **overrides):
        arguments = {
            "broker_code": "11",
            "symbol": "NABIL",
            "execution_channel_windows": self.windows,
            "market_context": self.context,
            "decision_time": "2026-11-26T16:00:00+05:45",
            "as_of_session": "2026-11-26",
            "minimum_daily_flow_multiple": 1.5,
        }
        arguments.update(overrides)
        return evaluate_broker_early_pattern(**arguments)

    def test_detects_early_entry_candidate_only_with_multi_horizon_flow_and_context(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "EARLY_ENTRY_CANDIDATE")
        self.assertEqual(result["calibration_status"], "uncalibrated_research_rule")
        self.assertIsNone(result["confidence"])
        self.assertFalse(result["beneficial_ownership_or_intent_inferred"])
        self.assertFalse(result["production_recommendations_enabled"])

    def test_detects_early_exit_risk_on_daily_reversal_with_extended_price(self):
        self.windows["1D"]["execution_channels"][0]["flow_class"] = "net_seller"
        self.windows["1D"]["execution_channels"][0]["latest_sell_vs_prior_20_avg_ratio"] = 2.2
        self.context["price_extension_status"] = "extended"
        result = self.evaluate()
        self.assertEqual(result["status"], "EARLY_EXIT_RISK")

    def test_missing_nepse_context_fails_closed(self):
        self.context["component_statuses"]["sector_index"] = "unknown"
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "unverified_nepse_context_components")

    def test_incomplete_monthly_window_fails_closed(self):
        self.windows["1M"]["window_complete"] = False
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "broker_horizon_incomplete")

    def test_future_market_context_fails_no_lookahead(self):
        self.context["available_at"] = "2026-11-26T17:00:00+05:45"
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "market_context_not_available_at_decision_time")

    def test_market_context_session_must_match_requested_as_of(self):
        self.context["as_of_session"] = "2026-11-25"
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "market_context_session_mismatch")

    def test_missing_20_session_baseline_fails_closed(self):
        self.windows["1D"]["execution_channels"][0]["prior_20_session_count"] = 9
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "insufficient_20_session_baseline")

    def test_boolean_daily_ratio_is_not_accepted_as_numeric_evidence(self):
        self.windows["1D"]["execution_channels"][0]["latest_buy_vs_prior_20_avg_ratio"] = True
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "daily_flow_baseline_ratio_invalid")

    def test_non_finite_daily_ratio_fails_closed(self):
        self.windows["1D"]["execution_channels"][0]["latest_buy_vs_prior_20_avg_ratio"] = float("inf")
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "daily_flow_baseline_ratio_invalid")

    def test_very_large_integer_daily_ratio_does_not_raise_overflow(self):
        self.windows["1D"]["execution_channels"][0]["latest_buy_vs_prior_20_avg_ratio"] = 10 ** 1000
        result = self.evaluate()
        self.assertEqual(result["status"], "EARLY_ENTRY_CANDIDATE")

    def test_very_large_integer_threshold_does_not_raise_overflow(self):
        result = self.evaluate(minimum_daily_flow_multiple=10 ** 1000)
        self.assertEqual(result["status"], "WATCH")

    def test_coverage_above_100_percent_fails_closed(self):
        self.windows["1D"]["coded_amount_coverage_pct"] = 100.01
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "broker_execution_code_coverage_out_of_range")

    def test_negative_daily_ratio_fails_closed(self):
        self.windows["1D"]["execution_channels"][0]["latest_buy_vs_prior_20_avg_ratio"] = -0.1
        result = self.evaluate()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["reason"], "daily_flow_baseline_ratio_invalid")


if __name__ == "__main__":
    unittest.main()

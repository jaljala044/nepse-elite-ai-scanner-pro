import unittest
from app.broker_intelligence_dashboard import (
    BrokerDashboardError, build_broker_intelligence_dashboard,
)


def profile(window, coverage="1", status="descriptive_only"):
    return {
        "broker_id": "B17", "security_id": "SEC-CFCL", "window": window,
        "status": status, "coverage_ratio": coverage,
        "requested_sessions": {"daily": 1, "weekly": 5, "monthly": 21, "yearly": 252}[window],
        "expected_sessions": {"daily": 1, "weekly": 5, "monthly": 21, "yearly": 252}[window],
        "complete_source_sessions": {"daily": 1, "weekly": 5, "monthly": 21, "yearly": 252}[window],
        "buy_amount": "100", "sell_amount": "20", "net_amount": "80",
        "gross_amount": "120", "buy_quantity": "10", "sell_quantity": "2",
        "net_quantity": "8", "positive_net_sessions": 3,
        "negative_net_sessions": 1, "zero_activity_sessions": 1,
        "positive_net_session_ratio": "0.6", "negative_net_session_ratio": "0.2",
        "broker_participation_ratio": "0.25",
        "daily": [{"session_date": "2026-11-26", "net_amount": "80"}],
        "directional_summary": "net_buy_dominant",
    }


def payload():
    return {
        "as_of_date": "2026-11-26",
        "as_of_timestamp": "2026-11-26T12:00:00+05:45",
        "rolling_profiles": {
            "as_of_date": "2026-11-26",
            "as_of_timestamp": "2026-11-26T11:00:00+05:45",
            "profiles": [profile(x) for x in ("daily", "weekly", "monthly", "yearly")],
            "excluded_observation_rows": 2,
            "verified_exchange_sessions": 252,
            "complete_source_sessions": 250,
        },
        "source_manifest": {
            "status": "verified", "source_ids": ["FLOORSHEET_A", "FLOORSHEET_B"],
            "coverage": "0.98", "available_at": "2026-11-26T10:00:00+05:45",
        },
        "sector_rotation_by_window": {},
        "candidates": [],
    }


class BrokerDashboardTests(unittest.TestCase):
    def build(self, data=None):
        return build_broker_intelligence_dashboard(**(data or payload()))

    def test_composes_daily_weekly_monthly_yearly_profiles(self):
        result = self.build()
        self.assertEqual(result["status"], "descriptive_only")
        self.assertEqual(result["data_quality"], "MEDIUM_CONFIDENCE")
        self.assertEqual(
            set(result["brokers"][0]["windows"]),
            {"daily", "weekly", "monthly", "yearly"},
        )
        self.assertEqual(result["brokers"][0]["windows"]["yearly"]["net_amount"], "80")
        self.assertEqual(result["missing_data_policy"], "UNKNOWN_NOT_ZERO_NO_IMPUTATION")

    def test_missing_window_is_unknown_not_zero(self):
        data = payload()
        data["rolling_profiles"]["profiles"] = [
            profile(x) for x in ("daily", "weekly", "monthly")
        ]
        result = self.build(data)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["brokers"][0]["windows"]["yearly"]["status"], "unavailable")
        self.assertIsNone(result["brokers"][0]["windows"]["yearly"].get("net_amount"))

    def test_low_coverage_manifest_withholds_profile_values(self):
        data = payload()
        data["source_manifest"]["coverage"] = "0.8"
        result = self.build(data)
        self.assertEqual(result["status"], "withheld")
        self.assertEqual(result["data_quality"], "LOW_CONFIDENCE")
        self.assertEqual(result["brokers"][0]["windows"]["daily"]["status"], "insufficient_evidence")
        self.assertIsNone(result["brokers"][0]["windows"]["daily"]["net_amount"])

    def test_unverified_manifest_withholds(self):
        data = payload()
        data["source_manifest"]["status"] = "unverified"
        result = self.build(data)
        self.assertEqual(result["status"], "withheld")
        self.assertEqual(result["source_manifest"]["reason"], "source_manifest_not_verified")

    def test_profile_after_cutoff_rejected(self):
        data = payload()
        data["rolling_profiles"]["as_of_timestamp"] = "2026-11-27T09:00:00+05:45"
        with self.assertRaises(BrokerDashboardError):
            self.build(data)

    def test_profile_date_mismatch_rejected(self):
        data = payload()
        data["rolling_profiles"]["as_of_date"] = "2026-11-25"
        with self.assertRaises(BrokerDashboardError):
            self.build(data)

    def test_rotation_window_requires_matching_as_of(self):
        data = payload()
        data["sector_rotation_by_window"]["weekly"] = {
            "status": "descriptive_only", "as_of_date": "2026-11-25",
            "as_of_timestamp": "2026-11-26T10:00:00+05:45", "brokers": [],
        }
        with self.assertRaises(BrokerDashboardError):
            self.build(data)

    def test_late_candidate_is_withheld(self):
        data = payload()
        data["candidates"] = [{
            "symbol": "CFCL", "as_of_date": "2026-11-26",
            "available_at": "2026-11-27T09:00:00+05:45",
            "classification": "early_accumulation_candidate",
            "action": "WATCH_FOR_CONFIRMATION",
        }]
        result = self.build(data)
        self.assertEqual(result["market_candidates"][0]["status"], "withheld")
        self.assertEqual(result["market_candidates"][0]["action"], "NO_TRADE")
        self.assertIsNone(result["market_candidates"][0]["probability"])

    def test_naive_timestamp_rejected(self):
        data = payload()
        data["as_of_timestamp"] = "2026-11-26T12:00:00"
        with self.assertRaises(BrokerDashboardError):
            self.build(data)


if __name__ == "__main__":
    unittest.main()

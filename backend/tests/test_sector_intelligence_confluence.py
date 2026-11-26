import unittest

from app.sector_intelligence_confluence import build_sector_intelligence_confluence


CUTOFF = "2026-11-26T14:30:00+05:45"
CURRENT_DATES = ["2026-11-22", "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"]


def market_fixture():
    return {
        "status": "observed", "as_of_session": "2026-11-26",
        "source_ids": {"stocks": ["stock-source"], "benchmark": ["nepse-source"]},
        "sectors": {
            "BANK": {
                "score_status": "observed", "classification": "Leading",
                "weighted_excess_return_pct": 8.2,
                "windows": {
                    "1W": {"median_excess_return_pct": 2.1},
                    "1M": {"median_excess_return_pct": 5.2},
                    "3M": {"median_excess_return_pct": 8.0},
                },
            },
            "HYDRO": {
                "score_status": "observed", "classification": "Lagging",
                "weighted_excess_return_pct": -4.1,
                "windows": {
                    "1W": {"median_excess_return_pct": -1.0},
                    "1M": {"median_excess_return_pct": -3.0},
                    "3M": {"median_excess_return_pct": -5.0},
                },
            },
        },
    }


def broker_fixture():
    return {
        "status": "descriptive_only",
        "as_of_date": "2026-11-26",
        "as_of_timestamp": "2026-11-26T14:00:00+05:45",
        "prior_complete_sessions": ["2026-11-12", "2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"],
        "current_complete_sessions": CURRENT_DATES,
        "brokers": [
            {"broker_id": "broker-1", "sectors": [
                {"sector": "BANK", "prior_buy_amount": "100", "prior_sell_amount": "90",
                 "current_buy_amount": "250", "current_sell_amount": "80"},
                {"sector": "HYDRO", "prior_buy_amount": "80", "prior_sell_amount": "90",
                 "current_buy_amount": "50", "current_sell_amount": "120"},
            ]},
            {"broker_id": "broker-2", "sectors": [
                {"sector": "BANK", "prior_buy_amount": "100", "prior_sell_amount": "100",
                 "current_buy_amount": "150", "current_sell_amount": "100"},
                {"sector": "HYDRO", "prior_buy_amount": "80", "prior_sell_amount": "80",
                 "current_buy_amount": "60", "current_sell_amount": "90"},
            ]},
        ],
    }


class SectorIntelligenceConfluenceTests(unittest.TestCase):
    def test_price_and_broker_rotation_are_joined(self):
        result = build_sector_intelligence_confluence(
            market_fixture(), broker_fixture(), decision_time=CUTOFF
        )
        self.assertEqual(result["status"], "observed_descriptive")
        self.assertFalse(result["signals_enabled"])
        self.assertEqual(result["sectors"]["BANK"]["confluence"],
                         "price_strength_and_broker_participation_broadening")
        self.assertEqual(result["sectors"]["BANK"]["broker_flow"]["current_net_amount"], "220")
        self.assertEqual(result["sectors"]["HYDRO"]["confluence"],
                         "price_weakness_and_net_broker_selling")

    def test_mismatched_market_and_broker_dates_withheld(self):
        broker = broker_fixture()
        broker["as_of_date"] = "2026-11-25"
        result = build_sector_intelligence_confluence(
            market_fixture(), broker, decision_time=CUTOFF
        )
        self.assertEqual(result["reason"], "market_broker_as_of_session_mismatch")

    def test_future_broker_snapshot_withheld(self):
        broker = broker_fixture()
        broker["as_of_timestamp"] = "2026-11-26T14:31:00+05:45"
        result = build_sector_intelligence_confluence(
            market_fixture(), broker, decision_time=CUTOFF
        )
        self.assertEqual(result["reason"], "broker_data_not_available_by_decision_time")

    def test_broker_window_must_end_on_market_session(self):
        broker = broker_fixture()
        broker["current_complete_sessions"] = ["2026-11-19", "2026-11-22", "2026-11-23", "2026-11-24", "2026-11-25"]
        result = build_sector_intelligence_confluence(
            market_fixture(), broker, decision_time=CUTOFF
        )
        self.assertEqual(result["reason"], "broker_window_does_not_end_on_market_session")

    def test_market_insufficient_evidence_withholds_confluence(self):
        market = market_fixture()
        market["status"] = "insufficient_evidence"
        result = build_sector_intelligence_confluence(
            market, broker_fixture(), decision_time=CUTOFF
        )
        self.assertEqual(result["reason"], "market_rotation_not_observed")

    def test_broker_provenance_gap_is_explicit(self):
        result = build_sector_intelligence_confluence(
            market_fixture(), broker_fixture(), decision_time=CUTOFF
        )
        self.assertFalse(result["broker_provenance_complete"])
        self.assertEqual(result["broker_provenance_status"],
                         "not_exposed_by_upstream_broker_contract")

    def test_duplicate_broker_identity_rejected(self):
        broker = broker_fixture()
        broker["brokers"].append(dict(broker["brokers"][0]))
        with self.assertRaisesRegex(ValueError, "broker_ids_must_be_nonempty_and_unique"):
            build_sector_intelligence_confluence(
                market_fixture(), broker, decision_time=CUTOFF
            )

    def test_naive_decision_time_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone_aware"):
            build_sector_intelligence_confluence(
                market_fixture(), broker_fixture(), decision_time="2026-11-26T14:30:00"
            )


if __name__ == "__main__":
    unittest.main()

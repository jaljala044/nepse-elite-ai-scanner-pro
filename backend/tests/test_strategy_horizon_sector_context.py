import unittest

from app.strategy_horizon_sector_context import build_strategy_horizon_sector_context, HORIZONS, STRATEGIES

SESSION = "2026-11-27"


def fixture():
    windows = {
        "1W": {"status": "observed", "median_excess_return_pct": 2.0},
        "1M": {"status": "observed", "median_excess_return_pct": 3.0},
        "3M": {"status": "observed", "median_excess_return_pct": 4.0},
        "6M": {"status": "observed", "median_excess_return_pct": 5.0},
    }
    return {
        "status": "observed", "mode": "descriptive_only",
        "as_of_session": SESSION,
        "source_ids": {"stocks": ["stock-capture"], "benchmark": ["nepse-capture"]},
        "sectors": {"HYDRO": {
            "score_status": "observed", "classification": "Leading",
            "relative_strength_rank_pct": 90,
            "weighted_excess_return_pct": 4.0,
            "windows": windows,
        }},
    }


def membership():
    return {"BENH": {
        "status": "verified", "source_id": "security-master",
        "source_payload_sha256": "a" * 64,
        "effective_from": "2026-01-01", "effective_to": None,
        "sector_code": "HYDRO",
    }}


class StrategyHorizonSectorContextTests(unittest.TestCase):
    def test_builds_all_24_strategy_horizon_contexts(self):
        result = build_strategy_horizon_sector_context(
            "BENH", fixture(), symbol_sector_membership=membership(),
            decision_session=SESSION,
        )
        self.assertEqual(result["status"], "observed_descriptive")
        self.assertEqual(set(result["strategies"]), set(STRATEGIES))
        self.assertTrue(all(set(result["strategies"][s]) == set(HORIZONS) for s in STRATEGIES))

    def test_horizon_window_selection_and_alignment(self):
        result = build_strategy_horizon_sector_context(
            "BENH", fixture(), symbol_sector_membership=membership(),
            decision_session=SESSION,
        )
        self.assertEqual(result["strategies"]["trend_momentum"]["t_plus_2"]["sector_context"]["horizon_windows"], {"1W": 2.0})
        self.assertEqual(result["strategies"]["hybrid_consensus"]["swing"]["sector_context"]["horizon_windows"], {"1W": 2.0, "1M": 3.0})
        self.assertEqual(result["strategies"]["fundamental_investment"]["positional"]["sector_context"]["alignment"], "supportive")

    def test_investment_horizon_is_withheld_without_12m_24m(self):
        result = build_strategy_horizon_sector_context(
            "BENH", fixture(), symbol_sector_membership=membership(),
            decision_session=SESSION,
        )
        context = result["strategies"]["fundamental_investment"]["investment"]["sector_context"]
        self.assertEqual(context["status"], "insufficient_evidence")
        self.assertEqual(context["required_additional_windows"], ["12M", "24M"])

    def test_broker_flow_is_not_inferred(self):
        result = build_strategy_horizon_sector_context(
            "BENH", fixture(), symbol_sector_membership=membership(),
            decision_session=SESSION,
        )
        context = result["strategies"]["broker_footprint"]["swing"]
        self.assertEqual(context["strategy_specific_evidence_status"], "broker_flow_unavailable")
        self.assertEqual(context["action"], "NO_CHANGE")

    def test_neutral_or_negative_alignment_does_not_adjust_scores(self):
        data = fixture()
        data["sectors"]["HYDRO"]["windows"]["1M"]["median_excess_return_pct"] = -1
        result = build_strategy_horizon_sector_context(
            "BENH", data, symbol_sector_membership=membership(),
            decision_session=SESSION,
        )
        context = result["strategies"]["trend_momentum"]["swing"]["sector_context"]
        self.assertEqual(context["alignment"], "mixed")
        self.assertEqual(context["score_adjustment"], 0)
        self.assertFalse(context["recommendation_override"])

    def test_stale_rotation_is_withheld(self):
        result = build_strategy_horizon_sector_context(
            "BENH", fixture(), symbol_sector_membership=membership(),
            decision_session="2026-11-28",
        )
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_unverified_membership_is_withheld(self):
        data = membership()
        data["BENH"]["source_payload_sha256"] = "bad"
        result = build_strategy_horizon_sector_context(
            "BENH", fixture(), symbol_sector_membership=data,
            decision_session=SESSION,
        )
        self.assertEqual(result["reason"], "effective_dated_symbol_sector_membership_unverified")

    def test_membership_outside_effective_period_is_withheld(self):
        data = membership()
        data["BENH"]["effective_to"] = "2026-11-26"
        result = build_strategy_horizon_sector_context(
            "BENH", fixture(), symbol_sector_membership=data,
            decision_session=SESSION,
        )
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_missing_source_lineage_is_withheld(self):
        data = fixture()
        data["source_ids"]["stocks"] = []
        result = build_strategy_horizon_sector_context(
            "BENH", data, symbol_sector_membership=membership(),
            decision_session=SESSION,
        )
        self.assertEqual(result["reason"], "rotation_source_lineage_missing")

    def test_missing_horizon_window_is_withheld(self):
        data = fixture()
        data["sectors"]["HYDRO"]["windows"]["1M"]["status"] = "insufficient_evidence"
        result = build_strategy_horizon_sector_context(
            "BENH", data, symbol_sector_membership=membership(),
            decision_session=SESSION,
        )
        context = result["strategies"]["trend_momentum"]["swing"]["sector_context"]
        self.assertEqual(context["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()

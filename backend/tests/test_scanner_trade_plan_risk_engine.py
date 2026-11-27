import unittest
from app.scanner_trade_plan import build_evidence_backed_trade_plan
from app.scanner_risk_engine import calculate_risk_limited_position, evaluate_execution_constraints

CUTOFF = "2026-11-27T12:00:00+05:45"
AVAILABLE = "2026-11-27T11:00:00+05:45"

def level(price, **extra):
    return {"price": price, "evidence_status": "verified", "source_id": "SRC",
            "evidence_id": "EV", "available_at": AVAILABLE, **extra}

class TradePlanTests(unittest.TestCase):
    def base_levels(self):
        return {"entry": {"low": "100", "high": "102", **level("100")},
                "stop": level("95"), "T1": level("120"),
                "T2": level("130"), "T3": level("145")}

    def test_builds_net_rr_using_worst_entry_and_costs(self):
        result = build_evidence_backed_trade_plan(symbol="TEST", horizon="swing",
            decision_time=CUTOFF, levels=self.base_levels(),
            round_trip_cost_pct="0.4", slippage_pct="0.2")
        self.assertEqual(result["status"], "research_plan_ready_for_human_review")
        self.assertEqual(result["entry"]["high"], "102")
        self.assertGreater(float(result["net_reward_risk"]["T1"]), 2)
        self.assertFalse(result["production_enabled"])

    def test_missing_levels_are_unavailable_not_inferred(self):
        result = build_evidence_backed_trade_plan(symbol="TEST", horizon="swing",
            decision_time=CUTOFF, levels={}, round_trip_cost_pct=0, slippage_pct=0)
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIn("entry", result["unavailable_levels"])
        self.assertIsNone(result["stop"])

    def test_future_or_unverified_levels_rejected(self):
        levels = self.base_levels()
        levels["stop"] = level("95", available_at="2026-11-27T13:00:00+05:45")
        result = build_evidence_backed_trade_plan(symbol="TEST", horizon="swing",
            decision_time=CUTOFF, levels=levels, round_trip_cost_pct=0, slippage_pct=0)
        self.assertIsNone(result["stop"])
        self.assertEqual(result["action"], "NO_TRADE")

    def test_bad_structure_and_target_order_rejected(self):
        levels = self.base_levels()
        levels["T2"] = level("119")
        result = build_evidence_backed_trade_plan(symbol="TEST", horizon="swing",
            decision_time=CUTOFF, levels=levels, round_trip_cost_pct=0, slippage_pct=0)
        self.assertIn("target_order_invalid:T2", result["errors"])

    def test_zone_requires_status_and_provenance(self):
        levels = self.base_levels()
        levels["support"] = [level("98", type="demand", strength="strong", status="tested"),
                             {"price": "97", "status": "tested"}]
        result = build_evidence_backed_trade_plan(symbol="TEST", horizon="swing",
            decision_time=CUTOFF, levels=levels, round_trip_cost_pct=0, slippage_pct=0)
        self.assertEqual(len(result["liquidity_map"]["support"]), 1)

class SharedRiskTests(unittest.TestCase):
    def params(self):
        return dict(equity=100000, available_cash=50000, entry_price=100,
            structural_stop=95, average_daily_volume=10000)

    def test_position_sizing_respects_risk_cash_allocation_and_adv(self):
        result = calculate_risk_limited_position(**self.params())
        self.assertGreater(result["quantity"], 0)
        self.assertLessEqual(result["quantity"], result["quantity_caps"]["risk"])
        self.assertLessEqual(result["quantity"], result["quantity_caps"]["cash"])
        self.assertLessEqual(result["quantity"], result["quantity_caps"]["liquidity_adv"])

    def test_hard_two_percent_cap_cannot_be_overridden(self):
        result = calculate_risk_limited_position(**self.params(), risk_pct=2.1)
        self.assertEqual(result["status"], "blocked")

    def test_gap_stress_reduces_position_size(self):
        low = calculate_risk_limited_position(**self.params(), settlement_gap_stress_pct=0)
        high = calculate_risk_limited_position(**self.params(), settlement_gap_stress_pct=10)
        self.assertLessEqual(high["quantity"], low["quantity"])

    def test_missing_adv_fails_closed(self):
        params = self.params()
        params["average_daily_volume"] = None
        result = calculate_risk_limited_position(**params)
        self.assertEqual(result["quantity"], 0)
        self.assertEqual(result["status"], "blocked")

    def test_execution_gate_blocks_stale_quote_and_circuit(self):
        result = evaluate_execution_constraints(quote_available=True, quote_age_seconds=20,
            max_quote_age_seconds=5, circuit_state="lower_circuit", spread_pct=1,
            max_spread_pct=2, bid_depth_value=100000)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("quote_stale", result["failures"])
        self.assertIn("circuit_or_halt_restriction", result["failures"])

    def test_execution_gate_requires_market_depth(self):
        result = evaluate_execution_constraints(quote_available=True, quote_age_seconds=1,
            max_quote_age_seconds=5, circuit_state="normal", spread_pct=0.5,
            max_spread_pct=2, bid_depth_value=500, required_exit_value=1000,
            broker_confirmed_sellable_quantity=10)
        self.assertIn("bid_depth_insufficient_for_exit", result["failures"])

if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date, timedelta
from app.execution_backtest import simulate_execution_scenario


COSTS = {
    "buy_broker_rate": "0.0036", "sell_broker_rate": "0.0036",
    "regulatory_rate": "0", "sell_dp_charge": "25",
    "capital_gain_tax_rate": "0.05", "slippage_bps": "10",
    "min_broker_fee": "10",
}


class ExecutionBacktestTests(unittest.TestCase):
    def setUp(self):
        start = date(2025, 1, 1)
        self.sessions = [(start + timedelta(days=i)).isoformat() for i in range(12)]
        self.rows = []
        self.reviewed = {}
        self.bands = {}
        for day in self.sessions:
            row = {"date": day, "open": 100.0, "high": 106.0,
                   "low": 99.0, "close": 104.0, "volume": 1000}
            self.rows.append(row)
            self.reviewed[("TEST", day)] = {
                **row, "symbol": "TEST", "security_id": "fixture-security",
                "instrument_type": "equity", "security_status": "active",
                "lifecycle_evidence_id": "fixture-lifecycle",
                "session_status": "verified_open", "session_evidence_id": "fixture-session",
                "source_id": "sharehub", "evidence_id": "fixture-" + day,
                "source_payload_sha256": "a" * 64, "price_basis_reviewed": True,
                "price_basis_status": "verified_unadjusted_no_actions",
                "corporate_action_status": "clear",
                "corporate_action_evidence_id": "fixture-action",
                "available_at": day + "T11:00:00+05:45",
            }
            self.bands[day] = {"lower": 90.0, "upper": 110.0,
                               "source_id": "fixture-band", "status": "scenario"}
        self.signal = {
            "schema_version": 1, "symbol": "TEST",
            "decision_time": self.sessions[0] + "T15:00:00+05:45",
            "horizon": "t_plus_2", "action": "BUY", "methodology": "fixture_v1",
            "evidence": [], "classification": "research_only_not_execution",
            "details": {"decision_date": self.sessions[0],
                        "plan": {"entry": "100", "stop": "95", "targets": ["105"]}},
        }
        self.config = {"tick_size": "0.1", "max_participation_pct": "0.05",
                       "min_turnover": "1000", "price_bands": self.bands}

    def run_scenario(self, **overrides):
        args = dict(signal=self.signal, rows=self.rows, verified_sessions=self.sessions,
                    evaluation_date=self.sessions[10], quantity=10,
                    cost_assumptions=COSTS, execution_config=self.config,
                    reviewed=self.reviewed)
        args.update(overrides)
        return simulate_execution_scenario(**args)

    def test_scenario_calculates_costs_and_respects_tick(self):
        result = self.run_scenario()
        self.assertEqual(result["status"], "scenario_completed")
        self.assertEqual(result["classification"], "hypothetical_execution_scenario_not_fill")
        self.assertEqual(result["scenario_quantity"], 10)
        self.assertEqual(result["buy_scenario_price"], "100.1")
        self.assertGreater(result["gross_pnl"], result["net_pnl"])
        self.assertFalse(result["production_eligible"])

    def test_missing_price_band_fails_closed(self):
        config = dict(self.config, price_bands={})
        result = self.run_scenario(execution_config=config)
        self.assertEqual(result["reason"], "dated_verified_price_band_inputs_required")

    def test_low_liquidity_turnover_withholds(self):
        rows = [dict(x) for x in self.rows]
        rows[1]["volume"] = 1
        reviewed = dict(self.reviewed)
        reviewed[("TEST", self.sessions[1])] = dict(reviewed[("TEST", self.sessions[1])], volume=1)
        result = self.run_scenario(rows=rows, reviewed=reviewed)
        self.assertEqual(result["reason"], "minimum_turnover_not_met")

    def test_circuit_lock_is_not_assumed_fill(self):
        rows = [dict(x) for x in self.rows]
        rows[1].update(open=110.0, high=110.0, low=110.0, close=110.0)
        reviewed = dict(self.reviewed)
        reviewed[("TEST", self.sessions[1])] = dict(reviewed[("TEST", self.sessions[1])], **rows[1])
        result = self.run_scenario(rows=rows, reviewed=reviewed)
        self.assertEqual(result["reason"], "buy_side_upper_circuit_lock_fill_unverified")

    def test_missing_cost_assumptions_withhold(self):
        result = self.run_scenario(cost_assumptions={"slippage_bps": 0})
        self.assertEqual(result["reason"], "complete_versioned_cost_assumptions_required")

    def test_invalid_quantity_rejected(self):
        result = self.run_scenario(quantity=1.5)
        self.assertEqual(result["reason"], "whole_share_quantity_required")


if __name__ == "__main__":
    unittest.main()

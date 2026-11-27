import unittest
from datetime import date, timedelta
from app.portfolio_backtest import run_portfolio_backtest


class PortfolioBacktestTests(unittest.TestCase):
    def setUp(self):
        self.days = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(10)]
        self.rows = {"AAA": [
            {"date": day, "open": 100, "high": 110, "low": 95,
             "close": close, "volume": 10000}
            for day, close in zip(self.days, [100, 100, 105, 110, 110, 110, 110, 110, 110, 110])
        ]}
        self.signal = {
            "classification": "research_only_not_execution", "symbol": "AAA",
            "decision_time": self.days[0] + "T15:00:00+05:45",
            "action": "BUY", "horizon": "t_plus_2",
            "details": {"decision_date": self.days[0],
                        "plan": {"entry": "100", "stop": "90", "targets": ["110"]}}
        }

    def runner(self, **kwargs):
        qty = kwargs["quantity"]
        return {
            "status": "scenario_completed", "entry_session": self.days[1],
            "exit_session": self.days[3], "scenario_quantity": min(qty, 1000),
            "buy_scenario_price": "100", "sell_scenario_price": "110",
            "buy_cash": float(min(qty, 1000) * 100),
            "sell_cash": float(min(qty, 1000) * 110),
            "net_pnl": float(min(qty, 1000) * 10),
            "net_return_pct": 10.0,
        }

    def run_portfolio(self, **overrides):
        args = dict(
            signals=[self.signal], rows_by_symbol=self.rows,
            verified_sessions_by_symbol={"AAA": self.days},
            evaluation_date=self.days[-1], portfolio_sessions=self.days,
            sector_by_symbol={"AAA": "Hydropower"},
            initial_capital=10000, max_positions=3,
            max_position_pct=0.20, max_sector_pct=0.40,
            risk_per_trade_pct=0.01,
            cost_assumptions_by_symbol={"AAA": {}},
            execution_config_by_symbol={"AAA": {}},
            scenario_runner=self.runner,
        )
        args.update(overrides)
        return run_portfolio_backtest(**args)

    def test_cash_risk_sizing_and_daily_equity_curve(self):
        result = self.run_portfolio()
        self.assertEqual(result["trade_count"], 1)
        self.assertEqual(result["trades"][0]["quantity"], 10)
        self.assertEqual(result["initial_capital"], 10000)
        self.assertAlmostEqual(result["ending_equity"], 10100)
        self.assertAlmostEqual(result["net_return_pct"], 1.0)
        self.assertEqual(len(result["equity_curve"]), 10)
        self.assertEqual(result["trades"][0]["cash_settlement_date"], self.days[5])
        self.assertEqual(result["cash_settlement"]["unsettled_receivable_count"], 0)
        self.assertEqual(result["classification"],
                         "portfolio_level_hypothetical_execution_scenario_not_exchange_fills")

    def test_sector_cap_prevents_second_same_sector_position(self):
        second = dict(self.signal, symbol="BBB")
        rows = dict(self.rows, BBB=[dict(x) for x in self.rows["AAA"]])
        result = self.run_portfolio(
            signals=[self.signal, second], rows_by_symbol=rows,
            verified_sessions_by_symbol={"AAA": self.days, "BBB": self.days},
            sector_by_symbol={"AAA": "Hydropower", "BBB": "Hydropower"},
            cost_assumptions_by_symbol={"AAA": {}, "BBB": {}},
            execution_config_by_symbol={"AAA": {}, "BBB": {}},
            max_sector_pct=0.10,
        )
        self.assertEqual(result["trade_count"], 1)
        self.assertTrue(any(x["reason"] == "capital_sector_or_risk_limit"
                            for x in result["withheld"]))


    def test_sale_proceeds_are_not_spendable_before_t_plus_2_settlement(self):
        second = dict(self.signal, symbol="BBB", decision_time=self.days[2] + "T15:00:00+05:45")
        rows = dict(self.rows, BBB=[dict(x) for x in self.rows["AAA"]])

        def delayed_runner(**kwargs):
            symbol = kwargs["signal"]["symbol"]
            qty = min(kwargs["quantity"], 1000)
            entry_day = self.days[1] if symbol == "AAA" else self.days[6]
            exit_day = self.days[3] if symbol == "AAA" else self.days[7]
            return {
                "status": "scenario_completed", "entry_session": entry_day,
                "exit_session": exit_day, "scenario_quantity": qty,
                "buy_scenario_price": "100", "sell_scenario_price": "100",
                "buy_cash": float(qty * 100), "sell_cash": float(qty * 100),
                "net_pnl": 0.0, "net_return_pct": 0.0,
            }

        result = self.run_portfolio(
            signals=[self.signal, second], rows_by_symbol=rows,
            verified_sessions_by_symbol={"AAA": self.days, "BBB": self.days},
            sector_by_symbol={"AAA": "Hydropower", "BBB": "Banking"},
            cost_assumptions_by_symbol={"AAA": {}, "BBB": {}},
            execution_config_by_symbol={"AAA": {}, "BBB": {}},
            initial_capital=1000, max_position_pct=1.0, max_sector_pct=1.0,
            risk_per_trade_pct=0.10, scenario_runner=delayed_runner,
        )
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual(result["trades"][0]["cash_settlement_date"], self.days[5])
        self.assertEqual(result["trades"][1]["entry_date"], self.days[6])

    def test_drawdown_breaker_blocks_later_entries(self):
        second = dict(self.signal, symbol="BBB", decision_time=self.days[2] + "T15:00:00+05:45")
        rows = dict(self.rows, BBB=[dict(x) for x in self.rows["AAA"]])

        def loss_then_later(**kwargs):
            symbol = kwargs["signal"]["symbol"]
            qty = min(kwargs["quantity"], 1000)
            return {
                "status": "scenario_completed",
                "entry_session": self.days[1] if symbol == "AAA" else self.days[4],
                "exit_session": self.days[3] if symbol == "AAA" else self.days[5],
                "scenario_quantity": qty, "buy_scenario_price": "100",
                "sell_scenario_price": "80" if symbol == "AAA" else "110",
                "buy_cash": float(qty * 100), "sell_cash": float(qty * (80 if symbol == "AAA" else 110)),
                "net_pnl": float(qty * (-20 if symbol == "AAA" else 10)),
                "net_return_pct": -20.0 if symbol == "AAA" else 10.0,
            }

        result = self.run_portfolio(
            signals=[self.signal, second], rows_by_symbol=rows,
            verified_sessions_by_symbol={"AAA": self.days, "BBB": self.days},
            sector_by_symbol={"AAA": "Hydropower", "BBB": "Banking"},
            cost_assumptions_by_symbol={"AAA": {}, "BBB": {}},
            execution_config_by_symbol={"AAA": {}, "BBB": {}},
            max_drawdown_pct=0.01, scenario_runner=loss_then_later,
        )
        self.assertTrue(result["circuit_breaker_triggered"])
        self.assertTrue(any(x["reason"] == "portfolio_drawdown_circuit_breaker_active"
                            for x in result["withheld"]))

    def test_duplicate_portfolio_sessions_rejected(self):
        with self.assertRaisesRegex(ValueError, "sorted_unique"):
            self.run_portfolio(portfolio_sessions=[self.days[0], self.days[0], self.days[-1]])

    def test_risk_budget_cannot_exceed_position_cap(self):
        with self.assertRaisesRegex(ValueError, "risk_budget_cannot_exceed_position_cap"):
            self.run_portfolio(risk_per_trade_pct=0.5)

    def test_noncanonical_portfolio_and_signal_dates_are_rejected(self):
        for day in ("20250101", "2025-1-01", "2025-01-01T00:00:00"):
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "canonical_iso_date"):
                self.run_portfolio(portfolio_sessions=[day, *self.days[1:]])
        with self.assertRaisesRegex(ValueError, "canonical_iso_date"):
            self.run_portfolio(evaluation_date="20250110")
        malformed_signal = dict(self.signal, details={
            "decision_date": "20250101",
            "plan": {"entry": "100", "stop": "90", "targets": ["110"]}
        })
        with self.assertRaisesRegex(ValueError, "canonical_iso_date"):
            self.run_portfolio(signals=[malformed_signal])

    def test_naive_signal_decision_timestamp_is_rejected(self):
        malformed_signal = dict(self.signal, decision_time=self.days[0] + "T15:00:00")
        with self.assertRaisesRegex(ValueError, "timezone_aware"):
            self.run_portfolio(signals=[malformed_signal])

    def test_boolean_risk_parameters_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_initial_capital"):
            self.run_portfolio(initial_capital=True)
        with self.assertRaisesRegex(ValueError, "invalid_max_drawdown_pct"):
            self.run_portfolio(max_drawdown_pct=True)


if __name__ == "__main__":
    unittest.main()

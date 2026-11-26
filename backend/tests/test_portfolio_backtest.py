import unittest
from datetime import date, timedelta
from app.portfolio_backtest import run_portfolio_backtest


class PortfolioBacktestTests(unittest.TestCase):
    def setUp(self):
        self.days = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(5)]
        self.rows = {"AAA": [
            {"date": day, "open": 100, "high": 110, "low": 95,
             "close": close, "volume": 10000}
            for day, close in zip(self.days, [100, 100, 105, 110, 110])
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
        self.assertEqual(len(result["equity_curve"]), 5)
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

    def test_duplicate_portfolio_sessions_rejected(self):
        with self.assertRaisesRegex(ValueError, "sorted_unique"):
            self.run_portfolio(portfolio_sessions=[self.days[0], self.days[0], self.days[-1]])

    def test_risk_budget_cannot_exceed_position_cap(self):
        with self.assertRaisesRegex(ValueError, "risk_budget_cannot_exceed_position_cap"):
            self.run_portfolio(risk_per_trade_pct=0.5)


if __name__ == "__main__":
    unittest.main()

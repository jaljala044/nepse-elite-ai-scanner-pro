from app.unified_portfolio_event_engine import run_unified_portfolio_event_ledger
import unittest

DAYS = ["2025-01-05", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09"]

def replay(trades):
    return run_unified_portfolio_event_ledger(
        initial_cash=1000, initial_holdings={},
        trades=trades, corporate_actions=[],
        price_rows_by_symbol={"ABC": [{"date": d, "close": 100} for d in DAYS]},
        portfolio_sessions=DAYS, as_of_date=DAYS[-1],
        evidence_cutoff="2025-01-10T00:00:00+00:00")

def trade(side, start, end):
    return dict(trade_id=side, symbol="ABC", side=side, quantity=5,
                price=100, fees=0, trade_date=DAYS[start],
                settlement_date=DAYS[end], status="verified",
                source_id="synthetic-test", available_at="2025-01-09T12:00:00+00:00")

class UnifiedPortfolioEventTests(unittest.TestCase):
    def test_settlement_preserves_equity_and_cash(self):
        result = replay([trade("BUY", 0, 2), trade("SELL", 2, 4)])
        curve = result["equity_curve"]
        assert [x["equity"] for x in curve] == [1000] * 5
        assert [x["cash"] for x in curve] == [500, 500, 500, 500, 1000]
        assert curve[2]["sale_receivables"] == 500

    def test_wrong_settlement_rejected(self):
        with self.assertRaisesRegex(ValueError, "t_plus_two"):
            replay([trade("BUY", 0, 1)])


    def test_paid_rights_carried_until_listing(self):
        action = dict(action_id="R", symbol="ABC", action_type="rights",
                      record_date=DAYS[0], subscription_payment_date=DAYS[1],
                      listing_date=DAYS[3], subscribed_quantity=2, ratio=0.5,
                      subscription_price=100, status="verified",
                      source_id="synthetic-test", available_at="2025-01-05T00:00:00+00:00")
        result = run_unified_portfolio_event_ledger(
            initial_cash=1000, initial_holdings={"ABC": {"quantity": 4, "average_cost": 100}},
            trades=[], corporate_actions=[action],
            price_rows_by_symbol={"ABC": [{"date": d, "close": 100} for d in DAYS]},
            portfolio_sessions=DAYS, as_of_date=DAYS[-1],
            evidence_cutoff="2025-01-10T00:00:00+00:00")
        curve = result["equity_curve"]
        assert [x["equity"] for x in curve] == [1400] * 5
        assert curve[1]["rights_paid_at_cost"] == 200
        assert curve[3]["rights_paid_at_cost"] == 0
        assert curve[3]["holdings"]["ABC"] == 6
        assert len(result["corporate_action_audit"]) == 2


    def test_event_ledger_api(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        payload = dict(initial_cash=1000, initial_holdings={}, trades=[],
                       corporate_actions=[], price_rows_by_symbol={},
                       portfolio_sessions=DAYS, as_of_date=DAYS[-1],
                       evidence_cutoff="2025-01-10T00:00:00+00:00")
        response = client.post("/v1/research/portfolio/event-ledger", json=payload)
        assert response.status_code == 200
        assert response.json()["ending_equity"] == 1000
        assert response.json()["production_eligible"] is False
        payload["initial_cash"] = -1
        assert client.post("/v1/research/portfolio/event-ledger", json=payload).status_code == 422


    def test_split_preserves_equity(self):
        action = dict(action_id="S", symbol="ABC", action_type="split",
                      record_date=DAYS[0], listing_date=DAYS[2], ratio=2,
                      status="verified", source_id="synthetic-test",
                      available_at="2025-01-05T00:00:00+00:00")
        result = run_unified_portfolio_event_ledger(
            initial_cash=1000, initial_holdings={"ABC": {"quantity": 4, "average_cost": 100}},
            trades=[], corporate_actions=[action],
            price_rows_by_symbol={"ABC": [{"date": d, "close": 100 if i < 2 else 50}
                                         for i, d in enumerate(DAYS)]},
            portfolio_sessions=DAYS, as_of_date=DAYS[-1],
            evidence_cutoff="2025-01-10T00:00:00+00:00")
        self.assertEqual([x["equity"] for x in result["equity_curve"]], [1400] * 5)
        self.assertEqual(result["equity_curve"][2]["holdings"]["ABC"], 8)


    def test_auto_size_respects_risk_and_liquidity(self):
        buy = dict(trade("BUY", 0, 2), auto_size=True, stop=90,
                   liquidity_quantity_cap=3, fees=2)
        result = run_unified_portfolio_event_ledger(
            initial_cash=1000, initial_holdings={}, trades=[buy],
            corporate_actions=[],
            price_rows_by_symbol={"ABC": [{"date": d, "close": 100} for d in DAYS]},
            portfolio_sessions=DAYS, as_of_date=DAYS[-1],
            evidence_cutoff="2025-01-10T00:00:00+00:00",
            sector_by_symbol={"ABC": "finance"},
            risk_limits=dict(max_position_pct=0.5, max_sector_pct=0.5,
                             risk_per_trade_pct=0.025, max_positions=2,
                             max_drawdown_pct=0.15))
        self.assertEqual(result["sized_trades"][0]["quantity"], 2)
        self.assertEqual(result["equity_curve"][2]["holdings"]["ABC"], 2)
        self.assertEqual(result["ending_equity"], 998)


    def test_linked_exit_uses_sized_quantity(self):
        buy = dict(trade("BUY", 0, 2), auto_size=True, stop=90,
                   liquidity_quantity_cap=3, fees=2, signal_id="synthetic-signal")
        sell = dict(trade("SELL", 2, 4), exit_entry_id="BUY",
                    signal_id="synthetic-signal")
        result = run_unified_portfolio_event_ledger(
            initial_cash=1000, initial_holdings={}, trades=[buy, sell],
            corporate_actions=[],
            price_rows_by_symbol={"ABC": [{"date": d, "close": 100} for d in DAYS]},
            portfolio_sessions=DAYS, as_of_date=DAYS[-1],
            evidence_cutoff="2025-01-10T00:00:00+00:00",
            sector_by_symbol={"ABC": "finance"},
            risk_limits=dict(max_position_pct=0.5, max_sector_pct=0.5,
                             risk_per_trade_pct=0.025, max_positions=2,
                             max_drawdown_pct=0.15))
        self.assertEqual([t["quantity"] for t in result["executed_trade_scenarios"]], [2, 2])
        self.assertEqual(result["equity_curve"][-1]["holdings"], {})
        self.assertEqual(result["ending_equity"], 998)


    def test_bonus_adjusted_linked_exit(self):
        days = DAYS + ["2025-01-12", "2025-01-13"]
        buy = trade("BUY", 0, 2)
        sell = dict(trade("SELL", 4, 4), settlement_date=days[6],
                    exit_entry_id="BUY", price=50)
        action = dict(action_id="B", symbol="ABC", action_type="bonus",
                      record_date=days[2], listing_date=days[3], ratio=1,
                      status="verified", source_id="synthetic-test",
                      available_at="2025-01-05T00:00:00+00:00")
        result = run_unified_portfolio_event_ledger(
            initial_cash=1000, initial_holdings={}, trades=[buy,sell],
            corporate_actions=[action],
            price_rows_by_symbol={"ABC": [{"date": d, "close": 100 if i < 3 else 50}
                                         for i,d in enumerate(days)]},
            portfolio_sessions=days, as_of_date=days[-1],
            evidence_cutoff="2025-01-14T00:00:00+00:00")
        self.assertEqual(result["executed_trade_scenarios"][-1]["quantity"], 10)
        self.assertEqual(result["ending_equity"], 1000)
        self.assertEqual(result["equity_curve"][-1]["holdings"], {})


    def test_signal_reconciliation_empty_portfolio(self):
        from app.portfolio_backtest import reconcile_signal_portfolio
        inputs = dict(signals=[], rows_by_symbol={}, verified_sessions_by_symbol={},
                      evaluation_date=DAYS[-1], portfolio_sessions=DAYS,
                      sector_by_symbol={}, initial_capital=1000, max_positions=2,
                      max_position_pct=0.5, max_sector_pct=0.5,
                      risk_per_trade_pct=0.025, cost_assumptions_by_symbol={},
                      execution_config_by_symbol={})
        result = reconcile_signal_portfolio(
            portfolio_inputs=inputs, evidence_cutoff="2025-01-10T00:00:00+00:00")
        self.assertEqual(result["ledger"]["ending_equity"], 1000)
        self.assertFalse(result["production_eligible"])
        with self.assertRaisesRegex(ValueError, "corporate_action_aware_signal_sizing"):
            reconcile_signal_portfolio(portfolio_inputs=inputs,
                evidence_cutoff="2025-01-10T00:00:00+00:00", corporate_actions=[{}])

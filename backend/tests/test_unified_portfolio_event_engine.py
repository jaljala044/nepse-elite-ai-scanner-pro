from app.unified_portfolio_event_engine import run_unified_portfolio_event_ledger
import pytest

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

def test_settlement_preserves_equity_and_cash():
    result = replay([trade("BUY", 0, 2), trade("SELL", 2, 4)])
    curve = result["equity_curve"]
    assert [x["equity"] for x in curve] == [1000] * 5
    assert [x["cash"] for x in curve] == [500, 500, 500, 500, 1000]
    assert curve[2]["sale_receivables"] == 500

def test_wrong_settlement_rejected():
    with pytest.raises(ValueError, match="t_plus_two"):
        replay([trade("BUY", 0, 1)])


def test_paid_rights_carried_until_listing():
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


def test_event_ledger_api():
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

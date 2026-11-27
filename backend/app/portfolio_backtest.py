"""Portfolio-level, chronological NEPSE research simulation.

This ledger is a conservative scenario, not a broker statement or exchange fill.
Sizing is based on prior-session marked equity; no future close is used to size a
trade. Only complete P4.44 execution scenarios are admitted.
"""
from __future__ import annotations

from collections import defaultdict
from math import floor, sqrt
from statistics import mean, pstdev

from .execution_backtest import simulate_execution_scenario
from .execution_constraints import settlement_date


def _finite(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("invalid_" + name) from None
    if not number > 0 or number == float("inf") or number != number:
        raise ValueError("invalid_" + name)
    return number


def _equity(cash, positions, receivables, mark_date, rows_by_symbol):
    value = cash + sum(float(x["amount"]) for x in receivables)
    for position in positions:
        bars = {str(x["date"]): x for x in rows_by_symbol[position["symbol"]]}
        bar = bars.get(mark_date)
        if bar is None:
            raise ValueError("portfolio_mark_bar_missing:" + position["symbol"] + ":" + mark_date)
        value += float(bar["close"]) * position["quantity"]
    return value


def _risk_metrics(curve):
    values = [float(x["equity"]) for x in curve]
    peak, max_dd = values[0], 0.0
    returns = []
    for previous, current in zip(values, values[1:]):
        if previous <= 0:
            raise ValueError("nonpositive_portfolio_equity")
        returns.append(current / previous - 1)
        peak = max(peak, current)
        max_dd = max(max_dd, (peak - current) / peak if peak else 0.0)
    sharpe = sortino = None
    if len(returns) >= 30:
        sigma = pstdev(returns)
        downside = [min(x, 0.0) for x in returns]
        downside_dev = (sum(x * x for x in downside) / len(downside)) ** 0.5
        sharpe = mean(returns) / sigma * sqrt(252) if sigma else None
        sortino = mean(returns) / downside_dev * sqrt(252) if downside_dev else None
    return {
        "daily_observations": len(returns),
        "max_drawdown_pct": max_dd * 100,
        "sharpe_annualized_zero_rf": sharpe,
        "sortino_annualized_zero_rf": sortino,
        "risk_adjusted_metrics_status": "descriptive_30_plus_daily_returns" if len(returns) >= 30 else "insufficient_daily_sample",
    }


def run_portfolio_backtest(*, signals, rows_by_symbol, verified_sessions_by_symbol,
                           evaluation_date, portfolio_sessions, sector_by_symbol,
                           initial_capital, max_positions, max_position_pct,
                           max_sector_pct, risk_per_trade_pct, cost_assumptions_by_symbol,
                           execution_config_by_symbol, reviewed=None, scenario_runner=None,
                           max_drawdown_pct=0.15):
    """Run chronological long-only portfolio simulation with cash/exposure controls."""
    initial = _finite(initial_capital, "initial_capital")
    if not isinstance(max_positions, int) or isinstance(max_positions, bool) or max_positions < 1:
        raise ValueError("max_positions_must_be_positive_integer")
    limits = {}
    for name, value in (("max_position_pct", max_position_pct),
                        ("max_sector_pct", max_sector_pct),
                        ("risk_per_trade_pct", risk_per_trade_pct)):
        pct = float(value)
        if not 0 < pct <= 1:
            raise ValueError("invalid_" + name)
        limits[name] = pct
    if limits["risk_per_trade_pct"] > limits["max_position_pct"]:
        raise ValueError("risk_budget_cannot_exceed_position_cap")
    drawdown_limit = float(max_drawdown_pct)
    if not 0 < drawdown_limit <= 1:
        raise ValueError("invalid_max_drawdown_pct")
    if not isinstance(portfolio_sessions, list) or len(portfolio_sessions) < 2:
        raise ValueError("portfolio_verified_sessions_required")
    days = [str(x) for x in portfolio_sessions]
    if days != sorted(days) or len(days) != len(set(days)):
        raise ValueError("portfolio_sessions_must_be_sorted_unique")
    end = str(evaluation_date)
    days = [d for d in days if d <= end]
    if not days or days[-1] != end:
        raise ValueError("evaluation_date_must_be_verified_portfolio_session")
    runner = scenario_runner or simulate_execution_scenario
    unique, seen = [], set()
    for signal in signals:
        if not isinstance(signal, dict) or signal.get("classification") != "research_only_not_execution":
            raise ValueError("frozen_research_signals_required")
        import hashlib, json
        sid = hashlib.sha256(json.dumps(signal, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if sid in seen:
            continue
        seen.add(sid)
        if signal.get("action") == "BUY":
            unique.append((str(signal.get("decision_time", "")), sid, signal))
    unique.sort(key=lambda x: (x[0], x[1]))
    withheld = []
    candidates = []
    probe_quantity = 1_000_000_000
    for decision_time, sid, signal in unique:
        symbol = signal.get("symbol")
        if (symbol not in rows_by_symbol or symbol not in verified_sessions_by_symbol
                or symbol not in sector_by_symbol or symbol not in cost_assumptions_by_symbol
                or symbol not in execution_config_by_symbol):
            withheld.append({"signal_id": sid, "reason": "symbol_inputs_or_sector_missing"})
            continue
        scenario = runner(
            signal=signal, rows=rows_by_symbol[symbol],
            verified_sessions=verified_sessions_by_symbol[symbol],
            evaluation_date=end, quantity=probe_quantity,
            cost_assumptions=cost_assumptions_by_symbol[symbol],
            execution_config=execution_config_by_symbol[symbol], reviewed=reviewed)
        if scenario.get("status") != "scenario_completed":
            withheld.append({"signal_id": sid, "reason": scenario.get("reason", "scenario_unavailable")})
            continue
        if not isinstance(sector_by_symbol[symbol], str) or not sector_by_symbol[symbol].strip():
            withheld.append({"signal_id": sid, "reason": "sector_mapping_invalid"})
            continue
        if scenario["entry_session"] not in days or scenario["exit_session"] not in days:
            withheld.append({"signal_id": sid, "reason": "entry_or_exit_outside_portfolio_calendar"})
            continue
        candidates.append({"signal_id": sid, "signal": signal, "symbol": symbol,
                           "sector": sector_by_symbol[symbol], "probe": scenario,
                           "entry_date": scenario["entry_session"],
                           "exit_date": scenario["exit_session"]})
    candidates.sort(key=lambda x: (x["entry_date"], x["signal"].get("decision_time", ""), x["signal_id"]))
    by_entry = defaultdict(list)
    for candidate in candidates:
        by_entry[candidate["entry_date"]].append(candidate)

    cash = initial
    open_positions = []
    exits = defaultdict(list)
    settlements = defaultdict(list)
    receivables = []
    completed = []
    curve = []
    prior_day = None
    peak_equity = initial
    circuit_breaker_triggered = False
    for day in days:
        # Sale proceeds remain unsettled until the second following verified session.
        for receivable in settlements.pop(day, []):
            cash += receivable["amount"]
            receivables.remove(receivable)
        # Sell scenarios create receivables; they do not create spendable cash immediately.
        for position in exits.pop(day, []):
            open_positions.remove(position)
            receivable = {"amount": position["sell_cash"], "settlement_date": position["settlement_date"],
                          "signal_id": position["signal_id"]}
            receivables.append(receivable)
            settlements[position["settlement_date"]].append(receivable)
            completed.append({
                "signal_id": position["signal_id"], "symbol": position["symbol"],
                "sector": position["sector"], "entry_date": position["entry_date"],
                "exit_date": position["exit_date"], "cash_settlement_date": position["settlement_date"],
                "quantity": position["quantity"],
                "buy_cash": position["buy_cash"], "sell_cash": position["sell_cash"],
                "net_pnl": position["net_pnl"], "net_return_pct": position["net_return_pct"],
                "risk_budget_cash": position["risk_budget_cash"],
            })
        # Size against prior close marks only. First session starts with cash only.
        sizing_equity = cash if prior_day is None else _equity(cash, open_positions, receivables, prior_day, rows_by_symbol)
        for candidate in by_entry.get(day, []):
            if circuit_breaker_triggered:
                withheld.append({"signal_id": candidate["signal_id"], "reason": "portfolio_drawdown_circuit_breaker_active"})
                continue
            if len(open_positions) >= max_positions:
                withheld.append({"signal_id": candidate["signal_id"], "reason": "max_open_positions_reached"})
                continue
            if any(p["symbol"] == candidate["symbol"] for p in open_positions):
                withheld.append({"signal_id": candidate["signal_id"], "reason": "same_symbol_position_already_open"})
                continue
            probe = candidate["probe"]
            symbol, sector = candidate["symbol"], candidate["sector"]
            entry_price = float(probe["buy_scenario_price"])
            stop = float(candidate["signal"].get("details", {}).get("plan", {}).get("stop",
                         candidate["signal"].get("details", {}).get("stop", 0)))
            risk_per_share = entry_price - stop
            if risk_per_share <= 0:
                withheld.append({"signal_id": candidate["signal_id"], "reason": "invalid_stop_risk_geometry"})
                continue
            sector_value = sum(float(p["mark_price"]) * p["quantity"] for p in open_positions if p["sector"] == sector)
            total_position_value = sum(float(p["mark_price"]) * p["quantity"] for p in open_positions)
            position_cap = sizing_equity * limits["max_position_pct"] - sum(
                float(p["mark_price"]) * p["quantity"] for p in open_positions if p["symbol"] == symbol)
            sector_cap = sizing_equity * limits["max_sector_pct"] - sector_value
            risk_budget = sizing_equity * limits["risk_per_trade_pct"]
            cash_budget = max(0.0, min(cash, position_cap, sector_cap,
                                       sizing_equity - total_position_value))
            risk_qty = floor(risk_budget / risk_per_share)
            capital_qty = floor(cash_budget / entry_price) if entry_price else 0
            quantity = min(int(probe["scenario_quantity"]), risk_qty, capital_qty)
            if quantity < 1:
                withheld.append({"signal_id": candidate["signal_id"], "reason": "capital_sector_or_risk_limit"})
                continue
            symbol_sessions = verified_sessions_by_symbol[symbol]
            scenario = runner(
                signal=candidate["signal"], rows=rows_by_symbol[symbol],
                verified_sessions=symbol_sessions, evaluation_date=end,
                quantity=quantity, cost_assumptions=cost_assumptions_by_symbol[symbol],
                execution_config=execution_config_by_symbol[symbol], reviewed=reviewed)
            if scenario.get("status") != "scenario_completed":
                withheld.append({"signal_id": candidate["signal_id"],
                                 "reason": scenario.get("reason", "sized_scenario_unavailable")})
                continue
            buy_cash = float(scenario["buy_cash"])
            sell_cash = float(scenario["sell_cash"])
            cash_settlement_day = settlement_date(scenario["exit_session"], symbol_sessions)
            if cash_settlement_day is None:
                withheld.append({"signal_id": candidate["signal_id"], "reason": "exit_cash_settlement_not_proven"})
                continue
            cash_settlement = cash_settlement_day.isoformat()
            if buy_cash > cash + 1e-8:
                withheld.append({"signal_id": candidate["signal_id"], "reason": "cash_budget_exceeded_after_costs"})
                continue
            cash -= buy_cash
            position = {
                "signal_id": candidate["signal_id"], "symbol": symbol, "sector": sector,
                "entry_date": scenario["entry_session"], "exit_date": scenario["exit_session"],
                "quantity": int(scenario["scenario_quantity"]), "buy_cash": buy_cash,
                "entry_price": float(scenario.get("buy_scenario_price", entry_price)),
                "exit_price": float(scenario["sell_scenario_price"]) if "sell_scenario_price" in scenario else None,
                "sell_cash": sell_cash, "settlement_date": cash_settlement,
                "net_pnl": float(scenario["net_pnl"]),
                "net_return_pct": float(scenario["net_return_pct"]),
                "risk_budget_cash": risk_budget, "mark_price": entry_price,
            }
            open_positions.append(position)
            exits[position["exit_date"]].append(position)
        # Daily mark-to-market close; missing bars are a hard failure, not zero valuation.
        close_equity = _equity(cash, open_positions, receivables, day, rows_by_symbol)
        for position in open_positions:
            bar = next(x for x in rows_by_symbol[position["symbol"]] if str(x["date"]) == day)
            position["mark_price"] = float(bar["close"])
        peak_equity = max(peak_equity, close_equity)
        drawdown = (peak_equity - close_equity) / peak_equity if peak_equity else 0.0
        if drawdown >= drawdown_limit:
            circuit_breaker_triggered = True
        receivable_value = sum(float(x["amount"]) for x in receivables)
        market_value = close_equity - cash - receivable_value
        curve.append({"date": day, "cash": round(cash, 8),
                      "receivables": round(receivable_value, 8),
                      "market_value": round(market_value, 8),
                      "equity": round(close_equity, 8),
                      "drawdown_pct": round(drawdown * 100, 8),
                      "open_positions": len(open_positions)})
        prior_day = day

    if open_positions:
        # Complete P4.44 scenarios should have exited by evaluation_date.
        raise ValueError("unclosed_positions_at_evaluation_date")
    wins = [x["net_pnl"] for x in completed if x["net_pnl"] > 0]
    losses = [x["net_pnl"] for x in completed if x["net_pnl"] < 0]
    gross_loss = -sum(losses)
    metrics = _risk_metrics(curve)
    return {
        "status": "completed_with_limitations",
        "classification": "portfolio_level_hypothetical_execution_scenario_not_exchange_fills",
        "methodology_version": "p4.45_portfolio_walk_forward_v1",
        "initial_capital": initial, "ending_equity": curve[-1]["equity"],
        "net_pnl": curve[-1]["equity"] - initial,
        "net_return_pct": (curve[-1]["equity"] / initial - 1) * 100,
        "trade_count": len(completed), "withheld_signal_count": len(withheld),
        "win_rate_pct": len(wins) / len(completed) * 100 if completed else None,
        "profit_factor": sum(wins) / gross_loss if gross_loss else (None if not wins else "undefined_no_losses"),
        "metrics": metrics, "equity_curve": curve, "trades": completed,
        "withheld": withheld,
        "risk_limits": {"max_positions": max_positions, "max_drawdown_pct": drawdown_limit, **limits},
        "cash_settlement": {"unsettled_receivable_count": len(receivables),
                            "unsettled_receivable_value": sum(float(x["amount"]) for x in receivables),
                            "cash_available_excludes_unsettled_proceeds": True},
        "circuit_breaker_triggered": circuit_breaker_triggered,
        "unavailable_metrics": ["benchmark_excess_return", "verified_realized_pnl",
                                "actual_fill_rate", "market_impact", "brokerage_statement_reconciliation"],
        "limitations": [
            "Hypothetical execution scenarios, not verified exchange fills or realized returns.",
            "Daily close marking and daily OHLCV cannot establish intraday liquidity or queue priority.",
            "Fees, tax, tick size, circuit bands, participation and turnover remain caller-supplied assumptions.",
            "Sector classification is caller-supplied; sector exposure is only as reliable as that mapping.",
            "No external benchmark or independently sourced official portfolio calendar is queried.",
            "No dividends, rights, bonus issues, splits, financing costs or cash interest are modeled.",
            "Risk sizing uses entry-to-stop price distance and does not guarantee the realized loss is capped."
        ]
    }


def reconcile_signal_portfolio(*, portfolio_inputs, evidence_cutoff, corporate_actions=None,
                               benchmark_rows=None, benchmark_symbol=None):
    """Replay frozen signal scenarios; fail closed on action-affected symbols.

    This is a reconciliation adapter, not corporate-action-aware signal sizing.
    """
    from .unified_portfolio_event_engine import run_unified_portfolio_event_ledger
    if corporate_actions:
        raise ValueError("corporate_action_aware_signal_sizing_not_available")
    result = run_portfolio_backtest(**portfolio_inputs)
    days = [x["date"] for x in result["equity_curve"]]
    trades = []
    for t in result["trades"]:
        symbol, sid, qty = t["symbol"], t["signal_id"], t["quantity"]
        if t["exit_price"] is None:
            raise ValueError("execution_scenario_price_missing")
        sessions = portfolio_inputs["verified_sessions_by_symbol"][symbol]
        buy_settle = settlement_date(t["entry_date"], sessions)
        if buy_settle is None:
            raise ValueError("entry_settlement_not_proven")
        for side, day, settle, price, fees in (
            ("BUY", t["entry_date"], buy_settle.isoformat(), t["entry_price"], t["buy_cash"]-qty*t["entry_price"]),
            ("SELL", t["exit_date"], t["settlement_date"], t["exit_price"], qty*t["exit_price"]-t["sell_cash"])):
            if fees < -1e-7:
                raise ValueError("execution_cost_reconciliation_failed")
            trades.append(dict(trade_id=sid+":"+side, signal_id=sid, symbol=symbol,
                               side=side, quantity=qty, price=price, fees=max(0,fees),
                               trade_date=day, settlement_date=settle, status="verified",
                               source_id="hypothetical_execution_scenario:"+sid,
                               available_at=evidence_cutoff))
    trades.sort(key=lambda t: (t["trade_date"], t["side"] != "SELL", t["trade_id"]))
    ledger = run_unified_portfolio_event_ledger(
        initial_cash=portfolio_inputs["initial_capital"], initial_holdings={},
        trades=trades, corporate_actions=[], price_rows_by_symbol=portfolio_inputs["rows_by_symbol"],
        portfolio_sessions=days, as_of_date=days[-1], evidence_cutoff=evidence_cutoff,
        benchmark_rows=benchmark_rows, benchmark_symbol=benchmark_symbol)
    for original, replay in zip(result["equity_curve"], ledger["equity_curve"]):
        if abs(original["equity"]-replay["equity"]) > 1e-5 or abs(original["cash"]-replay["cash"]) > 1e-5:
            raise ValueError("signal_portfolio_ledger_mismatch:"+original["date"])
    return {"classification":"hypothetical_signal_replay_reconciliation",
            "portfolio":result, "ledger":ledger, "production_eligible":False,
            "limitations":["No corporate-action-aware sizing; action inputs rejected.",
                           "Scenario evidence is not actual exchange trade evidence."]}

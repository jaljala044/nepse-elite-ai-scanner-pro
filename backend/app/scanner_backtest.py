"""Point-in-time, settlement-aware historical replay for six NEPSE strategies."""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from app.scanner_strategy_lab import HORIZONS, STRATEGIES

HOLDING_SESSIONS = {"t_plus_2": 5, "swing": 20, "positional": 60, "investment": 120}

def _d(value):
    try: x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): return None
    return x if x.is_finite() else None

def _dt(value):
    if not isinstance(value, str): return None
    try: x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    if x.tzinfo is None or x.utcoffset() is None: return None
    return x.astimezone(timezone.utc)

def _verified(item, cutoff=None):
    if not isinstance(item, dict) or item.get("evidence_status") != "verified": return False
    if not isinstance(item.get("source_id"), str) or not item["source_id"].strip(): return False
    if not isinstance(item.get("evidence_id"), str) or not item["evidence_id"].strip(): return False
    available = _dt(item.get("available_at"))
    return available is not None and (cutoff is None or available <= cutoff)

def _validated_bars(bars):
    if not isinstance(bars, list) or len(bars) < 2: raise ValueError("at_least_two_verified_bars_required")
    result, seen, previous = [], set(), None
    for bar in bars:
        if not isinstance(bar, dict) or not _verified(bar): raise ValueError("bar_missing_verified_provenance")
        try: day = date.fromisoformat(bar.get("date"))
        except (TypeError, ValueError): raise ValueError("invalid_bar_date") from None
        available = _dt(bar.get("available_at"))
        if available.date() < day: raise ValueError("bar_available_before_session_date")
        if day in seen: raise ValueError("duplicate_bar_date")
        if previous is not None and day <= previous: raise ValueError("bars_not_strictly_chronological")
        prices = {k: _d(bar.get(k)) for k in ("open", "high", "low", "close")}
        if any(v is None or v <= 0 for v in prices.values()): raise ValueError("invalid_ohlc")
        if prices["high"] < max(prices["open"], prices["close"], prices["low"]) or prices["low"] > min(prices["open"], prices["close"]):
            raise ValueError("inconsistent_ohlc")
        volume = _d(bar.get("volume"))
        if volume is None or volume < 0: raise ValueError("invalid_volume")
        result.append({**bar, "_date": day, "_prices": prices})
        seen.add(day); previous = day
    return result

def _net_return(entry, exit_price, total_cost_pct, total_slippage_pct):
    half = (total_cost_pct + total_slippage_pct) / Decimal("200")
    return exit_price * (Decimal("1") - half) / (entry * (Decimal("1") + half)) - Decimal("1")

def replay_strategy_horizon(*, strategy_id, horizon, signals, bars_by_symbol, partition,
    round_trip_cost_pct, round_trip_slippage_pct, sellable_after_sessions=2,
    initial_equity=Decimal("100000")):
    if strategy_id not in STRATEGIES: raise ValueError("unsupported_strategy")
    if horizon not in HOLDING_SESSIONS: raise ValueError("unsupported_horizon")
    if partition not in {"train", "validation", "out_of_sample"}: raise ValueError("explicit_partition_required")
    costs, slip, equity = _d(round_trip_cost_pct), _d(round_trip_slippage_pct), _d(initial_equity)
    if costs is None or slip is None or equity is None or min(costs, slip) < 0 or costs + slip >= 100 or equity <= 0:
        raise ValueError("invalid_cost_or_equity_assumption")
    if isinstance(sellable_after_sessions, bool) or not isinstance(sellable_after_sessions, int) or sellable_after_sessions < 0:
        raise ValueError("sellable_after_sessions_invalid")
    if not isinstance(signals, list) or not isinstance(bars_by_symbol, dict): raise ValueError("signals_and_bars_required")
    trades, rejected, pending, seen = [], [], [], set()
    for signal in signals:
        if not isinstance(signal, dict) or signal.get("strategy_id") != strategy_id or signal.get("horizon") != horizon or signal.get("sample_partition") != partition: continue
        symbol = str(signal.get("symbol", "")).strip().upper()
        try: decision_day = date.fromisoformat(signal.get("decision_date"))
        except (TypeError, ValueError):
            rejected.append({"symbol": symbol, "reason": "invalid_decision_date"}); continue
        key = (symbol, decision_day)
        if not symbol or key in seen:
            rejected.append({"symbol": symbol, "reason": "duplicate_or_invalid_signal_identity"}); continue
        seen.add(key)
        cutoff = _dt(signal.get("decision_time"))
        if cutoff is None or cutoff.date() != decision_day or not _verified(signal.get("stop"), cutoff) or not _verified(signal.get("target"), cutoff):
            rejected.append({"symbol": symbol, "reason": "signal_or_predecision_level_provenance_invalid"}); continue
        stop, target = _d(signal["stop"].get("price")), _d(signal["target"].get("price"))
        if stop is None or target is None or stop <= 0 or target <= 0:
            rejected.append({"symbol": symbol, "reason": "invalid_stop_or_target"}); continue
        try: bars = _validated_bars(bars_by_symbol.get(symbol))
        except ValueError as exc:
            rejected.append({"symbol": symbol, "reason": str(exc)}); continue
        next_indices = [i for i, b in enumerate(bars) if b["_date"] > decision_day]
        if not next_indices:
            rejected.append({"symbol": symbol, "reason": "next_session_bar_unavailable"}); continue
        entry_i = next_indices[0]; entry = bars[entry_i]["_prices"]["open"]
        if stop >= entry or target <= entry:
            rejected.append({"symbol": symbol, "reason": "long_stop_entry_target_structure_invalid"}); continue
        sellable_i = entry_i + sellable_after_sessions
        last_i = min(len(bars)-1, entry_i + HOLDING_SESSIONS[horizon]-1)
        exit_i = exit_price = reason = None; stop_pending = False
        for i in range(entry_i, last_i+1):
            p = bars[i]["_prices"]
            if stop_pending and i >= sellable_i:
                exit_i, exit_price, reason = i, p["open"], "stop_exit_after_settlement_lock"; break
            if i < sellable_i:
                if p["low"] <= stop: stop_pending = True
                continue
            if p["low"] <= stop:
                exit_i, exit_price, reason = i, stop, "stop"; break
            if p["high"] >= target:
                exit_i, exit_price, reason = i, target, "target"; break
        if exit_i is None:
            if last_i < sellable_i:
                pending.append({"symbol": symbol, "decision_date": decision_day.isoformat(), "source_signal_id": signal.get("signal_id"),
                    "reason": "holding_window_ended_before_sellable_session",
                    "last_observed_date": bars[last_i]["_date"].isoformat(),
                    "stop_triggered_while_locked": stop_pending}); continue
            exit_i, exit_price, reason = last_i, bars[last_i]["_prices"]["close"], "time_exit_close"
        gross = exit_price / entry - 1
        net = _net_return(entry, exit_price, costs, slip)
        observed_window = bars[entry_i:exit_i+1]
        max_favorable = max(b["_prices"]["high"] for b in observed_window) / entry - 1
        max_adverse = min(b["_prices"]["low"] for b in observed_window) / entry - 1
        trades.append({"symbol": symbol, "decision_date": decision_day.isoformat(),
            "entry_date": bars[entry_i]["_date"].isoformat(), "entry_price": str(entry),
            "exit_date": bars[exit_i]["_date"].isoformat(), "exit_price": str(exit_price),
            "exit_reason": reason, "stop_price": str(stop), "target_price": str(target),\n            "liquidity_quantity_cap": signal.get("liquidity_quantity_cap"),\n            "gross_return_pct": str(gross*100), "net_return_pct": str(net*100),
            "max_favorable_excursion_pct": str(max_favorable*100),
            "max_adverse_excursion_pct": str(max_adverse*100),
            "holding_sessions": exit_i-entry_i+1, "settlement_lock_sessions": sellable_after_sessions,
            "stop_triggered_during_lock": stop_pending, "source_signal_id": signal.get("signal_id")})
    wins = [_d(t["net_return_pct"]) for t in trades if _d(t["net_return_pct"]) > 0]
    losses = [_d(t["net_return_pct"]) for t in trades if _d(t["net_return_pct"]) < 0]
    returns = [_d(t["net_return_pct"]) for t in trades]
    total_wins, total_losses = sum(wins, Decimal("0")), abs(sum(losses, Decimal("0")))
    equity_value, peak, max_dd = equity, equity, Decimal("0")
    for value in returns:
        equity_value *= 1 + value/100; peak = max(peak, equity_value)
        max_dd = max(max_dd, (peak-equity_value)/peak if peak else Decimal("0"))
    avg = lambda xs: sum(xs, Decimal("0"))/len(xs) if xs else None
    metrics = {"sample_size":len(trades), "rejected_signals":len(rejected),
        "unclosed_or_settlement_pending":len(pending),
        "win_rate_pct":str(Decimal(len(wins))/len(trades)*100) if trades else None,
        "average_gain_pct":str(avg(wins)) if wins else None,
        "average_loss_pct":str(avg(losses)) if losses else None,
        "profit_factor":str(total_wins/total_losses) if total_losses else ("infinity" if total_wins else None),
        "expectancy_net_pct_per_trade":str(avg(returns)) if returns else None,
        "max_drawdown_pct":str(max_dd*100), "ending_equity":str(equity_value),
        "gross_return_pct_total":str(sum((_d(t["gross_return_pct"]) for t in trades), Decimal("0"))),
        "net_return_pct_compounded":str((equity_value/equity-1)*100),
        "target_exit_count":sum(t["exit_reason"]=="target" for t in trades),
        "stop_exit_count":sum(t["exit_reason"].startswith("stop") for t in trades),
        "time_exit_count":sum(t["exit_reason"]=="time_exit_close" for t in trades)}
    return {"schema_version":"nepse-replay-1.0.0","strategy_id":strategy_id,"horizon":horizon,
        "partition":partition,"metrics":metrics,"trades":trades,"rejected_signals":rejected,
        "pending_exits":pending,
        "assumptions":{"entry":"next available session open after signal date",
            "holding_sessions":HOLDING_SESSIONS[horizon],"round_trip_cost_pct":str(costs),
            "round_trip_slippage_pct":str(slip),"sellable_after_sessions":sellable_after_sessions,
            "intraday_collision":"stop_first","position_sizing":"one equal-notional trade per signal; no portfolio overlap/netting"},
        "limitations":["No live NEPSE dataset is bundled; replay requires externally verified signals and OHLCV.",
            "Settlement delay is a scenario input, not a claim about current settlement rules.",
            "No circuit queue, partial fills, market impact, corporate-action adjustment or portfolio concurrency model.",
            "Use untouched out_of_sample for model selection."],
        "performance_claimed":False,"production_enabled":False}

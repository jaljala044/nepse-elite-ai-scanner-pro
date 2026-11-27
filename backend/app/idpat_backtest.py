"""IDPAT-4 conservative OHLCV replay and chronological walk-forward helpers."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

HORIZONS = {"T+2": 5, "swing": 20, "positional": 126, "investment": 504}


class ReplayError(ValueError):
    pass


def _d(value, field):
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ReplayError(f"invalid_{field}") from None
    if not out.is_finite():
        raise ReplayError(f"invalid_{field}")
    return out


def _metrics(trades):
    if not trades:
        return {"sample_size": 0, "win_rate_pct": None, "average_gain_pct": None,
                "average_loss_pct": None, "profit_factor": None, "expectancy_pct": None,
                "max_drawdown_pct": None, "total_return_pct": None}
    returns = [Decimal(t["net_return_pct"]) for t in trades]
    wins, losses = [x for x in returns if x > 0], [x for x in returns if x < 0]
    gp, gl = sum(wins, Decimal(0)), abs(sum(losses, Decimal(0)))
    equity = peak = Decimal(1)
    max_dd = Decimal(0)
    for result in returns:
        equity *= 1 + result / 100
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak if peak else Decimal(0))
    pf = str(gp / gl) if gl else ("unbounded_no_losses" if wins else None)
    return {
        "sample_size": len(returns),
        "win_rate_pct": str(Decimal(len(wins)) / len(returns) * 100),
        "average_gain_pct": str(gp / len(wins)) if wins else None,
        "average_loss_pct": str(sum(losses, Decimal(0)) / len(losses)) if losses else None,
        "profit_factor": pf,
        "expectancy_pct": str(sum(returns, Decimal(0)) / len(returns)),
        "max_drawdown_pct": str(max_dd * 100),
        "total_return_pct": str((equity - 1) * 100),
    }


def replay_idpat_signals(*, signals, bars_by_symbol, as_of_date, as_of_timestamp,
                         round_trip_cost_pct, slippage_pct, min_sample_size=30):
    """Replay explicit signals only. Entry next session open; stop wins same-bar ties."""
    cutoff = date.fromisoformat(as_of_date)
    cutoff_ts = datetime.fromisoformat(str(as_of_timestamp).replace("Z", "+00:00"))
    costs, slip = _d(round_trip_cost_pct, "round_trip_cost_pct"), _d(slippage_pct, "slippage_pct")
    if cutoff_ts.tzinfo is None or costs < 0 or slip < 0 or costs + slip >= 100:
        raise ReplayError("invalid_cutoff_or_cost_model")
    if not isinstance(signals, list) or not isinstance(bars_by_symbol, dict):
        raise ReplayError("signals_and_bars_required")

    trades, rejected, seen = [], [], set()
    for sig in signals:
        try:
            symbol = sig["symbol"]
            signal_day = date.fromisoformat(str(sig["signal_date"]))
            entry_ref, stop, target = (_d(sig[k], k) for k in ("entry_reference", "stop", "target"))
            horizon = sig["horizon"]
            max_bars = HORIZONS[horizon]
        except (KeyError, TypeError, ValueError):
            rejected.append({"reason": "invalid_signal_contract"})
            continue
        key = (symbol, signal_day, horizon)
        if key in seen:
            rejected.append({"symbol": symbol, "reason": "duplicate_signal"})
            continue
        seen.add(key)
        if signal_day > cutoff or entry_ref <= 0 or stop <= 0 or stop >= entry_ref or target <= entry_ref:
            rejected.append({"symbol": symbol, "reason": "invalid_or_future_signal"})
            continue
        series = bars_by_symbol.get(symbol)
        if not isinstance(series, dict) or series.get("status") != "verified" or not series.get("source_id"):
            rejected.append({"symbol": symbol, "reason": "bar_source_not_verified_or_provenance_missing"})
            continue
        try:
            available = datetime.fromisoformat(str(series["available_at"]).replace("Z", "+00:00"))
            if available.tzinfo is None or available > cutoff_ts:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            rejected.append({"symbol": symbol, "reason": "bar_availability_invalid_or_late"})
            continue
        parsed, valid, previous = [], True, None
        for row in series.get("bars", []):
            try:
                day = date.fromisoformat(str(row["date"]))
                o, h, l, c = (_d(row[k], k) for k in ("open", "high", "low", "close"))
                if day > cutoff or (previous is not None and day <= previous):
                    valid = False
                    break
                if min(o, h, l, c) <= 0 or h < max(o, l, c) or l > min(o, h, c):
                    valid = False
                    break
                parsed.append({"date": day, "open": o, "high": h, "low": l, "close": c})
                previous = day
            except (KeyError, TypeError, ValueError):
                valid = False
                break
        if not valid:
            rejected.append({"symbol": symbol, "reason": "invalid_or_future_ohlc_history"})
            continue
        future = [b for b in parsed if b["date"] > signal_day]
        if len(future) < max_bars:
            rejected.append({"symbol": symbol, "reason": "full_horizon_history_unavailable"})
            continue
        entry_bar = future[0]
        entry_factor = 1 + (slip + costs / 2) / 100
        exit_factor = 1 - (slip + costs / 2) / 100
        entry = entry_bar["open"] * entry_factor
        if entry <= stop or entry >= target:
            rejected.append({"symbol": symbol, "reason": "next_open_outside_trade_bracket"})
            continue
        exit_price, exit_day, exit_reason = None, None, None
        for bar in future[:max_bars]:
            hit_stop, hit_target = bar["low"] <= stop, bar["high"] >= target
            if hit_stop:
                exit_price, exit_day, exit_reason = stop, bar["date"], "stop"
                break
            if hit_target:
                exit_price, exit_day, exit_reason = target, bar["date"], "target"
                break
        if exit_price is None:
            last = future[max_bars - 1]
            exit_price, exit_day, exit_reason = last["close"], last["date"], "horizon_close"
        net_exit = exit_price * exit_factor
        net_return = (net_exit / entry - 1) * 100
        trades.append({
            "symbol": symbol, "signal_date": signal_day.isoformat(),
            "entry_date": entry_bar["date"].isoformat(), "exit_date": exit_day.isoformat(),
            "entry_price_after_estimated_costs": str(entry),
            "exit_price_before_estimated_costs": str(exit_price),
            "exit_reason": exit_reason, "horizon": horizon,
            "net_return_pct": str(net_return), "source_id": series["source_id"],
        })

    enough = len(trades) >= min_sample_size
    return {
        "schema_version": "idpat-4.0.0",
        "status": "research_backtest" if enough else "insufficient_sample",
        "data_quality": "MEDIUM_CONFIDENCE" if enough else "LOW_CONFIDENCE",
        "as_of_date": cutoff.isoformat(),
        "cost_model": {"round_trip_cost_pct": str(costs),
                       "slippage_pct_per_side": str(slip),
                       "cost_and_slippage_split_across_entry_exit": True},
        "metrics": _metrics(trades), "trades": trades, "rejected_signals": rejected,
        "limitations": [
            "Only caller-supplied historical signals and verified OHLCV are replayed; no signals are invented.",
            "Next-session open entry; no intraday queue, partial fill, impact or order-book simulation.",
            "Stop is assumed first when stop and target both touch in one OHLC bar.",
            "Full horizon data is required; right-censored trades are rejected.",
            "Corporate actions, circuit limits, suspensions, settlement and actual fee/tax schedule must be represented upstream.",
            "Small samples remain LOW_CONFIDENCE; no predictive probability is emitted.",
        ],
    }


def walk_forward_split(records, *, train_fraction="0.70"):
    fraction = _d(train_fraction, "train_fraction")
    if not Decimal("0.5") <= fraction < Decimal("1"):
        raise ReplayError("train_fraction_must_be_0_5_to_less_than_1")
    ordered = sorted(records, key=lambda x: (str(x.get("signal_date", "")), str(x.get("symbol", ""))))
    if len(ordered) < 2:
        return {"status": "insufficient_history", "train": [], "test": []}
    split = max(1, min(len(ordered)-1, int(Decimal(len(ordered))*fraction)))
    return {"status": "chronological_split", "train": ordered[:split],
            "test": ordered[split:], "train_cutoff": ordered[split-1].get("signal_date"),
            "test_start": ordered[split].get("signal_date"), "no_random_shuffle": True}

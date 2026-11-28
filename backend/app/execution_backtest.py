"""NEPSE execution and cost scenario model.

All outputs are hypothetical scenarios, never exchange fills. Missing price-band,
calendar, liquidity or cost evidence fails closed. Long-only, cash-equity only.
"""
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, InvalidOperation

from .execution_costs import round_trip
from .effective_cost_schedule import resolve_cost_assumptions
from .strategy_horizon_policy import assess_holding_duration, HOLDING_BANDS
from .execution_constraints import settlement_date
from .signal_outcome_validation import evaluate_signal_path


def _canonical_day(value, name):
    if type(value) is date:
        return value.isoformat()
    if not isinstance(value, str):
        raise ValueError(name + "_must_be_canonical_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(name + "_must_be_canonical_iso_date") from None
    if parsed.isoformat() != value:
        raise ValueError(name + "_must_be_canonical_iso_date")
    return value


def _d(value, name, *, positive=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("invalid_" + name) from None
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError("invalid_" + name)
    return result


def _tick(price, tick, *, buy):
    rounding = ROUND_CEILING if buy else ROUND_FLOOR
    return (price / tick).to_integral_value(rounding=rounding) * tick


def _band_check(bar, band):
    try:
        low, high = _d(band["lower"], "band_lower"), _d(band["upper"], "band_upper")
        values = [_d(bar[k], "bar_" + k) for k in ("open", "high", "low", "close")]
    except (KeyError, ValueError):
        return False, "price_band_or_bar_missing"
    op, hi, lo, close = values
    if low <= 0 or high < low or lo < low or hi > high or not lo <= min(op, close) <= max(op, close) <= hi:
        return False, "bar_outside_supplied_price_band"
    if low == high:
        return False, "invalid_price_band"
    return True, None


def simulate_execution_scenario(*, signal, rows, verified_sessions, evaluation_date,
                                quantity, cost_assumptions, execution_config,
                                reviewed=None):
    """Estimate a conservative round trip from a complete reviewed signal path.

    execution_config requires tick_size, max_participation_pct, min_turnover,
    date-keyed price_bands and a separate supplied settlement calendar.
    Costs require complete dated scenario schedules.
    """
    base = {"classification": "hypothetical_execution_scenario_not_fill",
            "production_eligible": False, "status": "unavailable"}
    if not isinstance(signal, dict) or signal.get("action") != "BUY":
        return {**base, "reason": "long_buy_research_signal_required"}
    if signal.get("classification") != "research_only_not_execution":
        return {**base, "reason": "frozen_research_signal_required"}
    try:
        qty = _d(quantity, "quantity", positive=True)
        if qty != qty.to_integral_value():
            raise ValueError("whole_share_quantity_required")
        tick = _d(execution_config.get("tick_size"), "tick_size", positive=True)
        participation = _d(execution_config.get("max_participation_pct"), "max_participation_pct")
        min_turnover = _d(execution_config.get("min_turnover"), "min_turnover")
        if participation <= 0 or participation > 1:
            raise ValueError("participation_must_be_between_zero_and_one")
        if min_turnover < 0:
            raise ValueError("invalid_min_turnover")
        slip_bps = _d(cost_assumptions.get("slippage_bps"), "slippage_bps")
        if slip_bps < 0 or slip_bps >= 10000:
            raise ValueError("invalid_slippage_bps")
    except (AttributeError, ValueError) as exc:
        return {**base, "reason": str(exc)}

    try:
        evaluation_day = _canonical_day(evaluation_date, "evaluation_date")
        decision_day_text = _canonical_day(
            signal.get("details", {}).get("decision_date"), "signal_decision_date")
        session_days = [_canonical_day(day, "verified_session") for day in verified_sessions]
        if session_days != sorted(session_days) or len(session_days) != len(set(session_days)):
            raise ValueError("verified_sessions_must_be_sorted_unique")
    except (TypeError, ValueError) as exc:
        return {**base, "reason": str(exc)}

    try:
        outcome = evaluate_signal_path(signal, rows, session_days,
                                       evaluation_date=evaluation_day, reviewed=reviewed)
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        return {**base, "reason": "invalid_signal_path", "detail": str(exc)}
    if outcome.get("status") != "observed" or not outcome.get("entry_touched"):
        return {**base, "reason": "complete_reviewed_entry_path_required",
                "path_status": outcome.get("status"), "path_reason": outcome.get("reason")}
    by_day = {str(row["date"]): row for row in rows}
    entry_day = outcome.get("entry_reference_date")
    decision_day = date.fromisoformat(decision_day_text)
    future_window = [date.fromisoformat(day) for day in session_days
                     if decision_day < date.fromisoformat(day) <= date.fromisoformat(evaluation_day)]
    future_window = sorted(future_window)[:outcome.get("sessions_observed", 0)]
    exit_day = outcome.get("exit_reference_date") or (future_window[-1].isoformat() if future_window else None)
    if entry_day not in by_day or exit_day not in by_day:
        return {**base, "reason": "entry_or_exit_bar_missing"}
    entry_bar, exit_bar = by_day[entry_day], by_day[exit_day]
    bands = execution_config.get("price_bands")
    if not isinstance(bands, dict) or entry_day not in bands or exit_day not in bands:
        return {**base, "reason": "dated_verified_price_band_inputs_required"}
    for day, bar in ((entry_day, entry_bar), (exit_day, exit_bar)):
        valid, reason = _band_check(bar, bands[day])
        if not valid:
            return {**base, "reason": reason, "session": day}
    entry_ok, exit_ok = _band_check(entry_bar, bands[entry_day]), _band_check(exit_bar, bands[exit_day])
    if not entry_ok[0] or not exit_ok[0]:
        return {**base, "reason": "price_band_validation_failed"}

    def turnover(bar):
        return _d(bar.get("close"), "close", positive=True) * _d(bar.get("volume"), "volume")
    try:
        entry_turnover, exit_turnover = turnover(entry_bar), turnover(exit_bar)
        entry_volume, exit_volume = _d(entry_bar["volume"], "entry_volume"), _d(exit_bar["volume"], "exit_volume")
        if entry_turnover < min_turnover or exit_turnover < min_turnover:
            return {**base, "reason": "minimum_turnover_not_met",
                    "entry_turnover_proxy": str(entry_turnover), "exit_turnover_proxy": str(exit_turnover)}
        if entry_volume <= 0 or exit_volume <= 0:
            return {**base, "reason": "zero_volume_session"}
        if entry_volume != entry_volume.to_integral_value() or exit_volume != exit_volume.to_integral_value():
            return {**base, "reason": "fractional_volume"}
        entry_capacity = (entry_volume * participation).to_integral_value(rounding=ROUND_FLOOR)
        exit_capacity = (exit_volume * participation).to_integral_value(rounding=ROUND_FLOOR)
        filled_qty = min(qty, entry_capacity, exit_capacity)
        if filled_qty <= 0:
            return {**base, "reason": "participation_capacity_zero"}
        entry_plan = signal.get("details", {}).get("plan", signal.get("details", {}))
        entry_ref = _d(entry_plan.get("entry"), "entry", positive=True)
        stop_ref = _d(entry_plan.get("stop"), "stop", positive=True)
        if outcome.get("exit_reference") is not None:
            exit_ref = _d(outcome["exit_reference"], "exit_reference", positive=True)
        else:
            exit_ref = _d(outcome["mark_close"], "mark_close", positive=True)
        entry_open = _d(entry_bar["open"], "entry_open", positive=True)
        exit_open = _d(exit_bar["open"], "exit_open", positive=True)
        # A touched limit price can receive price improvement at a better open.
        raw_buy = min(entry_ref, entry_open)
        raw_sell = min(exit_ref, exit_open) if outcome.get("stop_touched") else max(exit_ref, exit_open) if exit_ref == stop_ref else exit_ref
        # Daily-bar lock limits have no demonstrated opposing liquidity: do not assume a fill.
        eband, xband = bands[entry_day], bands[exit_day]
        if (_d(entry_bar["high"], "high") == _d(entry_bar["low"], "low") == _d(eband["upper"], "upper")):
            return {**base, "reason": "buy_side_upper_circuit_lock_fill_unverified"}
        if (_d(exit_bar["high"], "high") == _d(exit_bar["low"], "low") == _d(xband["lower"], "lower")):
            return {**base, "reason": "sell_side_lower_circuit_lock_fill_unverified"}
        slip = slip_bps / Decimal("10000")
        buy_price = _tick(raw_buy * (1 + slip), tick, buy=True)
        sell_price = _tick(raw_sell * (1 - slip), tick, buy=False)
        entry_lower, entry_upper = _d(eband["lower"], "entry_band_lower"), _d(eband["upper"], "entry_band_upper")
        exit_lower, exit_upper = _d(xband["lower"], "exit_band_lower"), _d(xband["upper"], "exit_band_upper")
        if buy_price <= 0 or sell_price <= 0:
            return {**base, "reason": "invalid_slippage_adjusted_price"}
        if not entry_lower <= buy_price <= entry_upper:
            return {**base, "reason": "slippage_adjusted_buy_price_outside_circuit_band"}
        if not exit_lower <= sell_price <= exit_upper:
            return {**base, "reason": "slippage_adjusted_sell_price_outside_circuit_band"}
    except (KeyError, TypeError, ValueError) as exc:
        return {**base, "reason": str(exc)}

    settlement_days = execution_config.get("verified_settlement_days")
    if not isinstance(settlement_days, list):
        return {**base, "reason": "separate_settlement_calendar_required"}
    try:
        settlement_days = [_canonical_day(d, "settlement_day") for d in settlement_days]
        if settlement_days != sorted(set(settlement_days)):
            raise ValueError("settlement_calendar_not_sorted_unique")
        settled_on = settlement_date(entry_day, settlement_days)
    except (TypeError, ValueError) as exc:
        return {**base, "reason": str(exc)}
    if settled_on is None or date.fromisoformat(exit_day) <= settled_on:
        return {**base, "reason": "settlement_eligibility_not_proven",
                "required_settlement_date": str(settled_on) if settled_on else None,
                "exit_session": exit_day}
    # Apply supplied fee assumptions once; slippage has already been applied to prices.
    duration = None
    if signal.get("horizon") in HOLDING_BANDS:
        duration = assess_holding_duration(signal["horizon"], entry_day, exit_day,
                                          protective_exit=bool(outcome.get("stop_touched")))
        if not duration["duration_policy_allows_exit"]:
            return {**base, "reason": "holding_duration_outside_policy", "duration_policy": duration}
    try:
        fee_assumptions = resolve_cost_assumptions(entry_day, buy_price * filled_qty,
            sell_price * filled_qty, cost_assumptions, sell_date=exit_day,
            require_dated_charges=True)
        costs = round_trip(buy_price, sell_price, filled_qty,
                           assumptions={**fee_assumptions, "slippage_bps": "0"})
    except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError) as exc:
        return {**base, "reason": "dated_cost_schedule_invalid", "detail": str(exc)}
    if costs.get("status") != "scenario_only":
        return {**base, "reason": "complete_versioned_cost_assumptions_required"}
    return {
        **base, "status": "scenario_completed",
        "symbol": signal["symbol"], "horizon": signal["horizon"],
        "requested_quantity": int(qty), "scenario_quantity": int(filled_qty),
        "partial_quantity_scenario": filled_qty < qty,
        "entry_session": entry_day, "exit_session": exit_day,
        "settlement_eligible_from": str(settled_on),
        "entry_reference": str(entry_ref), "exit_reference": str(exit_ref),
        "buy_scenario_price": str(buy_price), "sell_scenario_price": str(sell_price),
        "entry_turnover_proxy": str(entry_turnover), "exit_turnover_proxy": str(exit_turnover),
        "entry_participation_pct": float(filled_qty / entry_volume * 100),
        "exit_participation_pct": float(filled_qty / exit_volume * 100),
        "gross_pnl": float((sell_price - buy_price) * filled_qty),
        "net_pnl": costs["net_pnl"], "net_return_pct": costs["net_return_pct"],
        "buy_fees": costs["buy_fees"], "sell_fees": costs["sell_fees"], "tax": costs["tax"],
        "cost_assumptions": costs["assumptions"],
        "cost_schedule_evidence": fee_assumptions["schedule_evidence"],
        "applied_slippage_bps": str(slip_bps),
        "duration_policy": duration,
        "execution_config": {"tick_size": str(tick), "max_participation_pct": str(participation),
                             "min_turnover": str(min_turnover)},
        "evidence_classification": "reviewed_daily_ohlcv_plus_caller_supplied_scenario_assumptions",
        "limitations": [
            "Scenario prices are not exchange fills; daily OHLCV cannot prove queue position or intraday liquidity.",
            "Price bands, tick size, fee rates, taxes, turnover thresholds and participation limits are caller-supplied assumptions, not certified historical official schedules.",
            "Turnover is approximated as close multiplied by volume, not verified exchange turnover.",
            "Settlement uses the supplied verified session list; no independent CDSC settlement feed is queried.",
            "Partial quantity is a capacity scenario, not evidence of a partial fill.",
            "Tax is simplified by the supplied scenario calculator and is not tax advice."
        ]
    }


def aggregate_execution_scenarios(scenarios):
    """Trade-level aggregate only; deliberately not a portfolio equity curve."""
    completed = [x for x in scenarios if x.get("status") == "scenario_completed"]
    pnls = [Decimal(str(x["net_pnl"])) for x in completed]
    returns = [Decimal(str(x["net_return_pct"])) for x in completed]
    gains = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    gross_gain, gross_loss = sum(gains, Decimal(0)), -sum(losses, Decimal(0))
    return {
        "classification": "trade_level_execution_scenario_summary_not_portfolio_backtest",
        "scenario_count": len(scenarios), "completed_scenarios": len(completed),
        "withheld_scenarios": len(scenarios) - len(completed),
        "total_net_pnl_scenario_sum": float(sum(pnls, Decimal(0))) if pnls else None,
        "average_net_return_pct_per_scenario": float(sum(returns, Decimal(0)) / len(returns)) if returns else None,
        "win_rate_pct": float(Decimal(len(gains)) / len(pnls) * 100) if pnls else None,
        "profit_factor": float(gross_gain / gross_loss) if gross_loss else (None if not gross_gain else "undefined_no_losses"),
        "metrics_scope": "independent trade scenarios; not compounded and not a portfolio equity curve",
        "portfolio_drawdown": None, "sharpe": None, "sortino": None,
    }

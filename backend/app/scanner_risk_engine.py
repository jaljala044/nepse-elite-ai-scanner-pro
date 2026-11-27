"""Shared position sizing and execution constraints for NEPSE research plans."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_FLOOR


def _d(value):
    try:
        x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return x if x.is_finite() else None


def calculate_risk_limited_position(
    *, equity, available_cash, entry_price, structural_stop,
    average_daily_volume, risk_pct=Decimal("1"),
    max_risk_pct=Decimal("2"), max_position_pct=Decimal("20"),
    max_adv_participation_pct=Decimal("5"), round_trip_cost_pct=Decimal("0"),
    slippage_pct=Decimal("0"), settlement_gap_stress_pct=Decimal("5"),
):
    """Return a conservative integer-share cap; no data means no executable size.

    ADV participation is a conservative capacity ceiling, not a promise of fills.
    Gap stress extends the assumed stop loss below the structural stop.
    """
    names = ("equity", "available_cash", "entry_price", "structural_stop",
             "average_daily_volume", "risk_pct", "max_risk_pct",
             "max_position_pct", "max_adv_participation_pct",
             "round_trip_cost_pct", "slippage_pct", "settlement_gap_stress_pct")
    raw = {
        "equity": equity, "available_cash": available_cash, "entry_price": entry_price,
        "structural_stop": structural_stop, "average_daily_volume": average_daily_volume,
        "risk_pct": risk_pct, "max_risk_pct": max_risk_pct,
        "max_position_pct": max_position_pct,
        "max_adv_participation_pct": max_adv_participation_pct,
        "round_trip_cost_pct": round_trip_cost_pct, "slippage_pct": slippage_pct,
        "settlement_gap_stress_pct": settlement_gap_stress_pct,
    }
    vals = {name: _d(raw[name]) for name in names}
    if any(v is None for v in vals.values()):
        return {"status": "blocked", "reason": "required_numeric_input_missing_or_invalid", "quantity": 0}
    v = vals
    if any(v[k] <= 0 for k in ("equity", "available_cash", "entry_price", "average_daily_volume")):
        return {"status": "blocked", "reason": "equity_cash_price_and_adv_must_be_positive", "quantity": 0}
    if v["structural_stop"] <= 0 or v["structural_stop"] >= v["entry_price"]:
        return {"status": "blocked", "reason": "structural_stop_must_be_below_entry", "quantity": 0}
    if v["risk_pct"] <= 0 or v["max_risk_pct"] <= 0 or v["risk_pct"] > v["max_risk_pct"] or v["max_risk_pct"] > 2:
        return {"status": "blocked", "reason": "risk_pct_exceeds_two_percent_cap_or_invalid", "quantity": 0}
    if not (0 < v["max_position_pct"] <= 100 and 0 < v["max_adv_participation_pct"] <= 100):
        return {"status": "blocked", "reason": "allocation_or_adv_participation_out_of_range", "quantity": 0}
    if min(v["round_trip_cost_pct"], v["slippage_pct"], v["settlement_gap_stress_pct"]) < 0:
        return {"status": "blocked", "reason": "cost_slippage_and_gap_stress_must_be_non_negative", "quantity": 0}
    if v["round_trip_cost_pct"] + v["slippage_pct"] >= 100 or v["settlement_gap_stress_pct"] >= 100:
        return {"status": "blocked", "reason": "cost_or_gap_assumption_out_of_range", "quantity": 0}

    half_rate = (v["round_trip_cost_pct"] + v["slippage_pct"]) / Decimal("200")
    stressed_stop = v["structural_stop"] * (Decimal("1") - v["settlement_gap_stress_pct"] / 100)
    effective_entry = v["entry_price"] * (Decimal("1") + half_rate)
    effective_exit = stressed_stop * (Decimal("1") - half_rate)
    risk_per_share = effective_entry - effective_exit
    if risk_per_share <= 0:
        return {"status": "blocked", "reason": "non_positive_stressed_risk_per_share", "quantity": 0}

    risk_budget = v["equity"] * v["risk_pct"] / 100
    allocation_budget = v["equity"] * v["max_position_pct"] / 100
    buy_cost_per_share = v["entry_price"] * (Decimal("1") + half_rate)
    risk_qty = (risk_budget / risk_per_share).to_integral_value(rounding=ROUND_FLOOR)
    cash_qty = (v["available_cash"] / buy_cost_per_share).to_integral_value(rounding=ROUND_FLOOR)
    allocation_qty = (allocation_budget / buy_cost_per_share).to_integral_value(rounding=ROUND_FLOOR)
    liquidity_qty = (v["average_daily_volume"] * v["max_adv_participation_pct"] / 100).to_integral_value(rounding=ROUND_FLOOR)
    quantity = max(Decimal("0"), min(risk_qty, cash_qty, allocation_qty, liquidity_qty))
    status = "sized_for_human_review" if quantity > 0 else "blocked"
    return {
        "status": status,
        "quantity": int(quantity),
        "limiting_constraint": min(
            (("risk", risk_qty), ("cash", cash_qty), ("allocation", allocation_qty), ("liquidity", liquidity_qty)),
            key=lambda item: item[1],
        )[0] if quantity > 0 else "no_positive_capacity",
        "risk_budget": str(risk_budget),
        "estimated_max_loss_including_cost_and_gap_stress": str(quantity * risk_per_share),
        "risk_per_share_stress_assumption": str(risk_per_share),
        "stressed_stop_price_scenario_not_forecast": str(stressed_stop),
        "quantity_caps": {"risk": int(risk_qty), "cash": int(cash_qty), "allocation": int(allocation_qty), "liquidity_adv": int(liquidity_qty)},
        "assumptions_pct": {
            "risk": str(v["risk_pct"]), "risk_hard_cap": str(v["max_risk_pct"]),
            "max_position": str(v["max_position_pct"]),
            "max_adv_participation": str(v["max_adv_participation_pct"]),
            "round_trip_cost": str(v["round_trip_cost_pct"]),
            "slippage": str(v["slippage_pct"]),
            "settlement_gap_stress": str(v["settlement_gap_stress_pct"]),
        },
        "warnings": [
            "ADV participation is a capacity ceiling only; actual depth, spread, circuits and fills must be checked.",
            "Gap stress is a scenario assumption, not a forecast or guaranteed maximum loss.",
            "Use broker-confirmed sellable quantity/date for exits; settlement restrictions are not inferred here.",
            "Whole-share sizing is a conservative quantity cap; verify current NEPSE lot and order rules before execution.",
            "Research sizing only; no order is placed.",
        ],
        "production_enabled": False,
    }


def evaluate_execution_constraints(
    *, quote_available, quote_age_seconds, max_quote_age_seconds,
    circuit_state, spread_pct, max_spread_pct, bid_depth_value,
    required_exit_value=None, broker_confirmed_sellable_quantity=None,
):
    """Fail-closed microstructure gate; caller supplies point-in-time broker facts."""
    failures = []
    if quote_available is not True:
        failures.append("quote_unavailable")
    if isinstance(quote_age_seconds, bool) or not isinstance(quote_age_seconds, (int, float)) or quote_age_seconds < 0:
        failures.append("quote_age_invalid")
    elif quote_age_seconds > max_quote_age_seconds:
        failures.append("quote_stale")
    if circuit_state not in {"normal", "upper_circuit", "lower_circuit", "halted", "unknown"}:
        failures.append("circuit_state_invalid")
    elif circuit_state != "normal":
        failures.append("circuit_or_halt_restriction")
    spread, max_spread, depth = _d(spread_pct), _d(max_spread_pct), _d(bid_depth_value)
    if spread is None or max_spread is None or spread < 0 or max_spread < 0 or spread > max_spread:
        failures.append("spread_unavailable_or_excessive")
    if depth is None or depth < 0:
        failures.append("bid_depth_unavailable_or_invalid")
    required = _d(required_exit_value) if required_exit_value is not None else None
    if required_exit_value is not None and (required is None or required < 0 or depth is None or depth < required):
        failures.append("bid_depth_insufficient_for_exit")
    if broker_confirmed_sellable_quantity is not None and (
        isinstance(broker_confirmed_sellable_quantity, bool)
        or not isinstance(broker_confirmed_sellable_quantity, int)
        or broker_confirmed_sellable_quantity < 0
    ):
        failures.append("broker_sellable_quantity_invalid")
    return {
        "status": "execution_checks_passed_for_human_review" if not failures else "blocked",
        "failures": failures,
        "broker_confirmed_sellable_quantity": broker_confirmed_sellable_quantity,
        "production_enabled": False,
        "warning": "A passing snapshot is not a fill guarantee; refresh quote, circuit, depth and sellable balance at order time.",
    }

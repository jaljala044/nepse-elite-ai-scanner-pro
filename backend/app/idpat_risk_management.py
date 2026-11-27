"""IDPAT-4 hypothetical long-only risk sizing and reward/risk gate."""
from decimal import Decimal, InvalidOperation, ROUND_FLOOR


class RiskPlanError(ValueError):
    pass


def _d(value, field):
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise RiskPlanError(f"invalid_{field}") from None
    if not out.is_finite():
        raise RiskPlanError(f"invalid_{field}")
    return out


def build_idpat_risk_plan(*, symbol, entry, stop, targets, capital,
                          risk_pct="1.0", max_risk_pct="2.0",
                          round_trip_cost_pct="0", slippage_pct="0",
                          average_daily_turnover=None,
                          max_turnover_participation_pct="5",
                          min_reward_risk="2.0", max_position_pct="20"):
    """All percentage inputs use percentage points (1.0 means 1%)."""
    if not isinstance(symbol, str) or not symbol.strip():
        raise RiskPlanError("symbol_required")
    e, s, c = _d(entry, "entry"), _d(stop, "stop"), _d(capital, "capital")
    rp, cap = _d(risk_pct, "risk_pct"), _d(max_risk_pct, "max_risk_pct")
    cost, slip = _d(round_trip_cost_pct, "round_trip_cost_pct"), _d(slippage_pct, "slippage_pct")
    min_rr, max_pos = _d(min_reward_risk, "min_reward_risk"), _d(max_position_pct, "max_position_pct")
    participation = _d(max_turnover_participation_pct, "max_turnover_participation_pct")
    if min(e, s, c) <= 0 or e <= s:
        raise RiskPlanError("long_entry_must_exceed_positive_stop_and_capital")
    if not (0 < rp <= cap <= 100):
        raise RiskPlanError("risk_pct_exceeds_configured_cap")
    if min(cost, slip, participation) < 0 or cost + slip >= 100:
        raise RiskPlanError("invalid_cost_or_participation")
    if not (0 < max_pos <= 100) or min_rr <= 0:
        raise RiskPlanError("invalid_position_or_reward_risk_limit")
    if not isinstance(targets, dict):
        raise RiskPlanError("targets_required")
    parsed = {}
    for name in ("T1", "T2", "T3"):
        if name in targets and targets[name] is not None:
            value = _d(targets[name], f"{name.lower()}_target")
            if value <= e:
                raise RiskPlanError(f"{name.lower()}_must_exceed_entry")
            parsed[name] = value
    if "T1" not in parsed:
        raise RiskPlanError("T1_required")

    risk_budget = c * rp / 100
    cost_rate = (cost + slip) / 100
    loss_per_share = e - s + (e + s) * cost_rate / 2
    qty_risk = (risk_budget / loss_per_share).to_integral_value(rounding=ROUND_FLOOR)
    qty_capital = ((c * max_pos / 100) / e).to_integral_value(rounding=ROUND_FLOOR)
    qty = min(qty_risk, qty_capital)
    liquidity_qty = None
    if average_daily_turnover is not None:
        turnover = _d(average_daily_turnover, "average_daily_turnover")
        if turnover < 0:
            raise RiskPlanError("negative_average_daily_turnover")
        liquidity_qty = (turnover * participation / 100 / e).to_integral_value(rounding=ROUND_FLOOR)
        qty = min(qty, liquidity_qty)

    target_results = {}
    for name, target in parsed.items():
        net_reward = target - e - (target + e) * cost_rate / 2
        ratio = net_reward / loss_per_share
        target_results[name] = {
            "target": str(target), "net_reward_per_share": str(net_reward),
            "net_reward_risk_ratio": str(ratio),
            "meets_minimum": net_reward > 0 and ratio >= min_rr,
        }
    reasons = []
    if qty < 1:
        reasons.append("position_size_below_one_share")
    if not target_results["T1"]["meets_minimum"]:
        reasons.append("T1_net_reward_risk_below_minimum")
    if average_daily_turnover is not None and liquidity_qty < 1:
        reasons.append("insufficient_turnover_capacity")
    notional = qty * e
    return {
        "schema_version": "idpat-4.0.0", "symbol": symbol,
        "status": "risk_plan_candidate" if not reasons else "rejected",
        "action": "REVIEW_ONLY" if not reasons else "NO_TRADE",
        "direction": "long_only", "capital": str(c), "risk_pct": str(rp),
        "risk_budget": str(risk_budget), "quantity_whole_shares": int(qty),
        "entry": str(e), "structural_stop": str(s),
        "invalidation": f"completed-session close below {s}",
        "position_notional": str(notional),
        "position_pct_of_capital": str(notional / c * 100),
        "estimated_risk_budget_used": str(qty * loss_per_share),
        "liquidity_capacity_shares": int(liquidity_qty) if liquidity_qty is not None else None,
        "targets": target_results, "minimum_reward_risk": str(min_rr),
        "estimated_cost_and_slippage_per_share": str((e + s) * cost_rate / 2),
        "rejection_reasons": reasons,
        "assumptions": [
            "Hypothetical long-only sizing; no order routing.",
            "Costs and slippage are caller estimates; zero means unmodelled, not free execution.",
            "Turnover participation is a coarse cap, not verified order-book depth or guaranteed liquidity.",
            "Independent market, sector, broker, data-quality and execution approval remains mandatory.",
        ],
    }

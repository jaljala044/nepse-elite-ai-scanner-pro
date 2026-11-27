"""Evidence-backed long trade plans; missing or unsupported levels stay unavailable."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

LEVEL_STATUSES = {"tested", "untested", "swept", "invalidated", "active"}


def _d(value):
    try:
        x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return x if x.is_finite() else None


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if x.tzinfo is None or x.utcoffset() is None:
        return None
    return x.astimezone(timezone.utc)


def _verified_level(level, cutoff, *, zone=False):
    if not isinstance(level, dict):
        return None
    price = _d(level.get("price"))
    available = _time(level.get("available_at"))
    if (
        price is None or price <= 0
        or level.get("evidence_status") != "verified"
        or not isinstance(level.get("source_id"), str) or not level["source_id"].strip()
        or not isinstance(level.get("evidence_id"), str) or not level["evidence_id"].strip()
        or available is None or available > cutoff
    ):
        return None
    result = {
        "price": str(price),
        "source_id": level["source_id"],
        "evidence_id": level["evidence_id"],
        "available_at": available.isoformat(),
    }
    if zone:
        status = level.get("status")
        if status not in LEVEL_STATUSES:
            return None
        result.update({"type": level.get("type"), "strength": level.get("strength"), "status": status})
    return result


def build_evidence_backed_trade_plan(
    *, symbol, horizon, decision_time, levels, round_trip_cost_pct,
    slippage_pct, minimum_net_reward_risk=Decimal("2")
):
    """Build a long plan from verified entry/stop/target and optional map levels.

    levels keys: entry={low,high,...shared provenance}, stop, T1/T2/T3,
    support/resistance/buy_side_liquidity/sell_side_liquidity (lists of zones).
    Prices and provenance must be sourced upstream; no technical levels are inferred.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol_required")
    if horizon not in {"t_plus_2", "swing", "positional", "investment"}:
        raise ValueError("unsupported_horizon")
    cutoff = _time(decision_time)
    if cutoff is None:
        raise ValueError("decision_time_must_be_timezone_aware")
    if not isinstance(levels, dict):
        levels = {}
    costs, slip, min_rr = map(_d, (round_trip_cost_pct, slippage_pct, minimum_net_reward_risk))
    if costs is None or slip is None or min_rr is None or min(costs, slip) < 0 or min_rr <= 0 or costs + slip >= 100:
        raise ValueError("invalid_cost_slippage_or_rr_assumption")
    rate = (costs + slip) / Decimal("100")

    entry_source = levels.get("entry")
    entry_low = entry_high = None
    entry_evidence = None
    if isinstance(entry_source, dict):
        entry_evidence = _verified_level(entry_source, cutoff)
        entry_low, entry_high = _d(entry_source.get("low")), _d(entry_source.get("high"))
        if entry_evidence is None or entry_low is None or entry_high is None or entry_low <= 0 or entry_high < entry_low:
            entry_low = entry_high = None

    verified = {name: _verified_level(levels.get(name), cutoff) for name in ("stop", "T1", "T2", "T3")}
    prices = {name: _d(value.get("price")) if value else None for name, value in verified.items()}
    errors = []
    if entry_low is None or entry_high is None:
        errors.append("verified_entry_range_unavailable")
    if prices["stop"] is None:
        errors.append("verified_structural_stop_unavailable")
    if prices["T1"] is None:
        errors.append("verified_T1_unavailable")
    if not errors:
        if not (prices["stop"] < entry_low <= entry_high < prices["T1"]):
            errors.append("long_entry_stop_T1_structure_invalid")
        for earlier, later in (("T1", "T2"), ("T2", "T3")):
            if prices[earlier] is not None and prices[later] is not None and prices[later] <= prices[earlier]:
                errors.append("target_order_invalid:" + later)
    rr = {}
    if not errors:
        # Conservative fill at the top of entry range, with round-trip costs/slippage.
        entry_effective = entry_high * (Decimal("1") + rate / 2)
        stop_effective = prices["stop"] * (Decimal("1") - rate / 2)
        risk = entry_effective - stop_effective
        for target in ("T1", "T2", "T3"):
            if prices[target] is not None:
                reward = prices[target] * (Decimal("1") - rate / 2) - entry_effective
                rr[target] = reward / risk if risk > 0 else None
        if rr.get("T1") is None or rr["T1"] < min_rr:
            errors.append("net_T1_reward_risk_below_minimum")

    def zones(name):
        raw = levels.get(name)
        if not isinstance(raw, list):
            return []
        return [v for v in (_verified_level(x, cutoff, zone=True) for x in raw) if v]

    plan_ok = not errors
    return {
        "schema_version": "evidence-trade-plan-1.0.0",
        "symbol": symbol.strip().upper(),
        "horizon": horizon,
        "decision_time": cutoff.isoformat(),
        "status": "research_plan_ready_for_human_review" if plan_ok else "withheld",
        "action": "RESEARCH_PLAN_ONLY" if plan_ok else "NO_TRADE",
        "entry": {"low": str(entry_low), "high": str(entry_high), **(entry_evidence or {})} if entry_low is not None else None,
        "stop": verified["stop"],
        "targets": {k: verified[k] for k in ("T1", "T2", "T3")},
        "net_reward_risk": {k: str(v) if v is not None else None for k, v in rr.items()},
        "minimum_net_T1_reward_risk": str(min_rr),
        "cost_assumptions_pct": {"round_trip_cost": str(costs), "slippage": str(slip)},
        "liquidity_map": {
            "support": zones("support"),
            "resistance": zones("resistance"),
            "buy_side_liquidity": zones("buy_side_liquidity"),
            "sell_side_liquidity": zones("sell_side_liquidity"),
        },
        "unavailable_levels": [k for k in ("entry", "stop", "T1", "T2", "T3") if (k == "entry" and entry_low is None) or (k != "entry" and verified[k] is None)],
        "errors": errors,
        "warnings": [
            "All price levels are source-supplied observations, not verified live order-book depth unless the source explicitly says so.",
            "A stop is an invalidation/risk trigger, not a guaranteed fill; gaps, circuits, no bids and settlement restrictions can prevent execution.",
            "This output is research-only and is not an order or a production BUY recommendation.",
        ],
        "production_enabled": False,
    }

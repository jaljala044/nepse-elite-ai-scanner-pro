"""P4.41 conservative, point-in-time NEPSE early entry/exit signal engine.

Consumes explicit upstream evidence; it does not fetch or attest live exchange data.
Broker flow is a descriptive confirmation only. Missing/late/weak evidence fails closed.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

HORIZONS = ("t_plus_2", "swing", "positional")
REGIMES_ALLOWED = {"bull", "accumulation", "markup"}
SETUPS = {"momentum_breakout", "reversal", "trend_continuation"}
ENTRY_TYPES = {"confirmed_breakout", "breakout_retest", "demand_pullback"}


class SignalEngineError(ValueError):
    """Invalid signal request or malformed evidence."""


def _time(value, field):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise SignalEngineError(f"invalid_{field}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SignalEngineError(f"{field}_must_be_timezone_aware")
    return parsed


def _decimal(value, field, *, positive=False, signed=False):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise SignalEngineError(f"invalid_{field}") from None
    if not number.is_finite() or (positive and number <= 0) or (not signed and not positive and number < 0):
        raise SignalEngineError(f"invalid_{field}")
    return number


def _verified(item, name, cutoff, minimum_coverage):
    if not isinstance(item, dict):
        return f"{name}_evidence_missing"
    if item.get("status") != "verified":
        return f"{name}_not_verified"
    source_ids = item.get("source_ids", [item.get("source_id")])
    if not isinstance(source_ids, list) or not source_ids or any(not isinstance(x, str) or not x.strip() for x in source_ids):
        return f"{name}_source_ids_missing"
    coverage = _decimal(item.get("coverage"), f"{name}_coverage")
    if coverage > 1 or coverage < minimum_coverage:
        return f"{name}_coverage_below_threshold"
    if _time(item.get("available_at"), f"{name}_available_at") > cutoff:
        return f"{name}_not_available_as_of_cutoff"
    return None


def _plan(horizon, plan, common, minimum_rr):
    result = {"horizon": horizon, "action": "NO_TRADE", "setup": None,
              "entry": None, "stop": None, "targets": [], "risk_pct": None,
              "reward_risk": None, "confidence": "LOW_CONFIDENCE", "reasons": []}
    if not isinstance(plan, dict):
        result["reasons"] = ["horizon_plan_missing"]
        return result
    setup = plan.get("setup")
    if setup not in SETUPS:
        result["reasons"] = ["unsupported_or_missing_setup"]
        return result
    entry_type = plan.get("entry_type")
    if entry_type not in ENTRY_TYPES or plan.get("confirmation") != "confirmed":
        result["reasons"] = ["entry_confirmation_missing"]
        return result
    try:
        entry = _decimal(plan.get("entry"), "entry", positive=True)
        stop = _decimal(plan.get("stop"), "stop", positive=True)
        targets = [_decimal(x, "target", positive=True) for x in plan.get("targets", [])]
    except SignalEngineError as exc:
        result["reasons"] = [str(exc)]
        return result
    if stop >= entry or not targets or any(x <= entry for x in targets):
        result["reasons"] = ["invalid_or_missing_trade_geometry"]
        return result
    targets = sorted(set(targets))
    risk = entry - stop
    first_rr = (targets[0] - entry) / risk
    if first_rr < minimum_rr:
        result["reasons"] = ["nearest_target_reward_risk_below_minimum"]
        return result
    if plan.get("invalidation_condition") != "close_below_stop":
        result["reasons"] = ["structural_invalidation_not_defined"]
        return result
    # Every price level must be explicitly attributed to a verified chart input.
    if plan.get("level_status") != "inferred_chart_level" or not plan.get("evidence_dates"):
        result["reasons"] = ["entry_stop_target_level_provenance_missing"]
        return result
    result.update({
        "action": "BUY", "setup": setup, "entry_type": entry_type,
        "entry": str(entry), "stop": str(stop),
        "targets": [{"label": f"T{i+1}", "price": str(value),
                     "reward_risk": str((value-entry)/risk)} for i, value in enumerate(targets[:3])],
        "risk_pct": str((risk / entry) * 100),
        "reward_risk": str(first_rr), "confidence": "MEDIUM_CONFIDENCE",
        "invalidation": {"condition": "close_below_stop", "price": str(stop)},
        "evidence_dates": sorted(set(plan["evidence_dates"])),
        "level_status": "inferred_chart_level",
        "reasons": ["all_common_evidence_gates_passed", "confirmed_price_structure",
                    "minimum_reward_risk_met", "broker_flow_used_as_confirmation_only"],
        "limitations": ["Gross reward/risk; fees, slippage and market impact not deducted",
                        "A signal is not an order or confirmed fill"],
    })
    return result


def _exit_review(horizon, evidence, cutoff, minimum_coverage):
    """Return a conservative exit review; absence of evidence is UNKNOWN, not HOLD."""
    result = {"horizon": horizon, "action": "NO_TRADE", "status": "unknown",
              "reasons": ["exit_evidence_missing"]}
    if not isinstance(evidence, dict):
        return result
    error = _verified(evidence, "exit", cutoff, minimum_coverage)
    if error:
        result["reasons"] = [error]
        return result
    by_horizon = evidence.get("horizons")
    item = by_horizon.get(horizon) if isinstance(by_horizon, dict) else None
    if not isinstance(item, dict) or item.get("status") != "confirmed":
        result["reasons"] = ["horizon_exit_review_not_confirmed"]
        return result
    triggers = item.get("triggers")
    allowed = {"structural_breakdown", "stop_triggered", "failed_breakout",
               "distribution_confirmed", "relative_strength_breakdown"}
    if not isinstance(triggers, list) or any(x not in allowed | {"none"} for x in triggers):
        result["reasons"] = ["invalid_exit_trigger_evidence"]
        return result
    active = sorted(set(triggers) - {"none"})
    if active:
        return {"horizon": horizon, "action": "SELL_OR_REDUCE",
                "status": "exit_trigger_confirmed", "triggers": active,
                "reasons": ["verified_exit_trigger_requires_risk_reduction"],
                "source_ids": evidence.get("source_ids", [evidence.get("source_id")])}
    if triggers == ["none"] or not triggers:
        return {"horizon": horizon, "action": "HOLD_WITH_CAUTION",
                "status": "no_exit_trigger_observed",
                "triggers": [], "reasons": ["verified_review_found_no_listed_exit_trigger"],
                "source_ids": evidence.get("source_ids", [evidence.get("source_id")])}
    return result


def generate_early_entry_exit_signals(snapshot: dict, *, as_of_date: str,
                                      as_of_timestamp: str,
                                      minimum_coverage: Decimal = Decimal("0.95"),
                                      minimum_reward_risk: Decimal = Decimal("2.0"),
                                      minimum_turnover: Decimal = Decimal("1000000"),
                                      maximum_spread_pct: Decimal = Decimal("2.0"),
                                      minimum_trades: int = 20,
                                      minimum_displayed_depth: Decimal = Decimal("100000")) -> dict:
    """Build horizon-separated research signals from verified, caller-supplied evidence."""
    if not isinstance(snapshot, dict):
        raise SignalEngineError("snapshot_required")
    cutoff_date = date.fromisoformat(as_of_date)
    cutoff = _time(as_of_timestamp, "as_of_timestamp")
    coverage_floor = _decimal(minimum_coverage, "minimum_coverage")
    rr_floor = _decimal(minimum_reward_risk, "minimum_reward_risk", positive=True)
    if coverage_floor <= 0 or coverage_floor > 1:
        raise SignalEngineError("minimum_coverage_out_of_range")
    if rr_floor < 2:
        raise SignalEngineError("minimum_reward_risk_must_be_at_least_two")
    symbol = snapshot.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        raise SignalEngineError("symbol_required")
    try:
        evidence_date = date.fromisoformat(str(snapshot.get("as_of_date")))
    except (TypeError, ValueError):
        raise SignalEngineError("invalid_snapshot_date") from None
    if evidence_date > cutoff_date or _time(snapshot.get("available_at"), "snapshot_available_at") > cutoff:
        return {"symbol": symbol, "status": "withheld", "action": "NO_TRADE",
                "data_quality": "LOW_CONFIDENCE", "reason": "snapshot_not_available_as_of_cutoff",
                "horizons": {h: {"action": "NO_TRADE", "reasons": ["late_snapshot"]} for h in HORIZONS},
                "probability": None}
    reasons = []
    for name in ("market", "sector", "liquidity", "broker", "price_volume", "candidate"):
        error = _verified(snapshot.get(name), name, cutoff, coverage_floor)
        if error:
            reasons.append(error)
    market = snapshot.get("market") or {}
    sector = snapshot.get("sector") or {}
    liquidity = snapshot.get("liquidity") or {}
    broker = snapshot.get("broker") or {}
    candidate = snapshot.get("candidate") or {}
    if market.get("regime") not in REGIMES_ALLOWED:
        reasons.append("market_regime_not_supportive_or_unknown")
    if sector.get("alignment") != "leading_or_improving" or _decimal(sector.get("excess_return_1m"), "sector_excess_return", signed=True) <= 0:
        reasons.append("sector_alignment_not_confirmed")
    try:
        turnover = _decimal(liquidity.get("median_turnover"), "median_turnover")
        spread = _decimal(liquidity.get("median_spread_pct"), "median_spread_pct")
        trades = int(liquidity.get("median_trade_count"))
        depth = _decimal(liquidity.get("median_displayed_depth"), "median_displayed_depth")
        if turnover < _decimal(minimum_turnover, "minimum_turnover") or spread > _decimal(maximum_spread_pct, "maximum_spread_pct") or trades < minimum_trades or depth < _decimal(minimum_displayed_depth, "minimum_displayed_depth"):
            reasons.append("liquidity_execution_threshold_failed")
    except (TypeError, ValueError, SignalEngineError):
        reasons.append("liquidity_metrics_missing_or_invalid")
    # Broker participation is only a corroborating descriptor, never a standalone trigger.
    try:
        net = _decimal(broker.get("net_amount"), "broker_net_amount", signed=True)
        persistence = _decimal(broker.get("positive_net_session_ratio"), "broker_positive_persistence")
        if net <= 0 or persistence < Decimal("0.60"):
            reasons.append("broker_flow_not_supportive")
    except SignalEngineError:
        reasons.append("broker_flow_metrics_missing")
    if candidate.get("classification") == "distribution_risk_candidate":
        reasons.append("distribution_risk_candidate")
    if candidate.get("classification") not in {"early_accumulation_candidate", "no_confirmed_candidate"}:
        reasons.append("candidate_classification_unavailable")
    if reasons:
        return {"symbol": symbol, "status": "withheld", "action": "NO_TRADE",
                "data_quality": "LOW_CONFIDENCE", "as_of_date": evidence_date.isoformat(),
                "available_at": _time(snapshot["available_at"], "snapshot_available_at").isoformat(),
                "common_reasons": sorted(set(reasons)),
                "horizons": {h: {"horizon": h, "action": "NO_TRADE",
                                  "confidence": "LOW_CONFIDENCE",
                                  "reasons": sorted(set(reasons))} for h in HORIZONS},
                "probability": None, "source_ids": sorted({sid for name in ("market","sector","liquidity","broker","price_volume","candidate")
                    for sid in ((snapshot.get(name) or {}).get("source_ids") or [(snapshot.get(name) or {}).get("source_id")]) if isinstance(sid,str) and sid.strip()})}
    horizons = {h: _plan(h, (snapshot.get("plans") or {}).get(h), snapshot, rr_floor) for h in HORIZONS}
    exit_reviews = {h: _exit_review(h, snapshot.get("exit_evidence"), cutoff, coverage_floor) for h in HORIZONS}
    actionable = [x for x in horizons.values() if x["action"] == "BUY"]
    exit_actions = [x for x in exit_reviews.values() if x["action"] == "SELL_OR_REDUCE"]
    overall = "SELL_OR_REDUCE" if exit_actions else ("BUY" if actionable else "NO_TRADE")
    return {"symbol": symbol, "status": "exit_review_required" if exit_actions else ("signal_ready" if actionable else "no_confirmed_setup"),
            "action": overall,
            "data_quality": "MEDIUM_CONFIDENCE" if actionable or exit_actions else "LOW_CONFIDENCE",
            "as_of_date": evidence_date.isoformat(),
            "available_at": _time(snapshot["available_at"], "snapshot_available_at").isoformat(),
            "market_regime": market.get("regime"),
            "candidate_classification": candidate.get("classification"),
            "horizons": horizons, "exit_reviews": exit_reviews, "probability": None,
            "source_ids": sorted({sid for name in ("market","sector","liquidity","broker","price_volume","candidate")
                for sid in ((snapshot.get(name) or {}).get("source_ids") or [(snapshot.get(name) or {}).get("source_id")]) if isinstance(sid,str) and sid.strip()}),
            "policy": "NEPSE_RESEARCH_ONLY_NO_ORDER_EXECUTION",
            "limitations": ["Caller-supplied upstream verification is not independently re-attested here",
                           "No probabilities or backtest metrics without calibrated walk-forward outcomes",
                           "Broker flow is descriptive confirmation, not proof of ownership or intent",
                           "Exit review is informational; no order, fill, or execution is generated"]}

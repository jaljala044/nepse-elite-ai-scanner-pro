"""Fail-closed Stage 3 horizon decision engine.

Consumes reviewed Stage 1 eligibility and evidence-backed Stage 2 features.
It does not calculate or invent chart levels, probabilities, or market data.
"""
from __future__ import annotations

from math import isfinite

HORIZONS = {
    "T+2": "3-5 trading days",
    "SWING": "1-4 weeks",
    "POSITIONAL": "1-6 months",
    "INVESTMENT": "6-24 months",
}
WEIGHTS = {
    "wyckoff": 0.25,
    "minervini": 0.25,
    "relative_strength": 0.15,
    "broker_footprint": 0.10,
    "volume_vsa": 0.10,
    "liquidity": 0.05,
    "sector": 0.05,
    "smc": 0.05,
}
RATING_BANDS = (
    (95, "Elite Opportunity"),
    (90, "Potential Market Leader"),
    (85, "Strong Buy Candidate"),
    (80, "Buy Watchlist"),
    (70, "Developing Setup"),
    (60, "Monitor"),
    (0, "Ignore"),
)


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def _score(components):
    if not isinstance(components, dict):
        components = {}
    accepted = {}
    missing = []
    for name in WEIGHTS:
        value = _number(components.get(name))
        if value is None or not 0 <= value <= 100:
            missing.append(name)
        else:
            accepted[name] = value
    coverage = sum(WEIGHTS[name] for name in accepted)
    if coverage == 0:
        return None, coverage, accepted, missing
    # Renormalize only observed components; coverage is always disclosed.
    score = sum(accepted[name] * WEIGHTS[name] for name in accepted) / coverage
    return round(score, 2), round(coverage, 4), accepted, missing


def _rating(score, coverage):
    if score is None or coverage < 0.75:
        return "Unrated - insufficient component coverage"
    return next(label for floor, label in RATING_BANDS if score >= floor)


def _valid_levels(plan):
    if not isinstance(plan, dict):
        return None
    entry_low = _number(plan.get("entry_low"))
    entry_high = _number(plan.get("entry_high"))
    stop = _number(plan.get("stop_loss"))
    targets = plan.get("targets") if isinstance(plan.get("targets"), dict) else {}
    t1 = _number(targets.get("t1"))
    t2 = _number(targets.get("t2")) if targets.get("t2") is not None else None
    t3 = _number(targets.get("t3")) if targets.get("t3") is not None else None
    if None in (entry_low, entry_high, stop, t1):
        return None
    if not (0 < stop < entry_low <= entry_high < t1):
        return None
    if targets.get("t2") is not None and (t2 is None or t2 <= t1):
        return None
    if targets.get("t3") is not None and (t3 is None or t2 is None or t3 <= t2):
        return None
    risk = entry_high - stop
    if risk <= 0:
        return None
    rr = (t1 - entry_high) / risk
    return {
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop_loss": stop,
        "targets": {"t1": t1, "t2": t2, "t3": t3},
        "risk_percent": round(risk / entry_high * 100, 4),
        "reward_risk": round(rr, 3),
    }


def evaluate_horizon(symbol, horizon, stage1, stage2, plan, evidence_refs=None,
                     holding=False):
    """Return one horizon decision. All missing/invalid gates fail closed."""
    if horizon not in HORIZONS:
        raise ValueError(f"unsupported horizon: {horizon}")
    stage1 = stage1 if isinstance(stage1, dict) else {}
    stage2 = stage2 if isinstance(stage2, dict) else {}
    structure = stage2.get("structure") if isinstance(stage2.get("structure"), dict) else {}
    plan = plan if isinstance(plan, dict) else {}
    refs = sorted({str(x) for x in (evidence_refs or []) if isinstance(x, str) and x.strip()})
    raw_level_refs = plan.get("evidence_refs", [])
    if not isinstance(raw_level_refs, (list, tuple, set)):
        raw_level_refs = []
    level_refs = sorted({x.strip() for x in raw_level_refs
                         if isinstance(x, str) and x.strip()})
    score, coverage, accepted, missing = _score(stage2.get("components"))
    rating = _rating(score, coverage)
    quality = str(stage1.get("data_quality", "LOW")).upper()
    reasons = []
    action, subtype = "NO_TRADE", "INSUFFICIENT_DATA"
    levels = _valid_levels(plan)
    rr = levels["reward_risk"] if levels else None

    hard_failures = []
    if stage1.get("eligible") is not True:
        hard_failures.append("stage1_not_eligible")
    if quality not in {"HIGH", "MEDIUM"}:
        hard_failures.append("data_quality_low_or_unknown")
    for key in ("identity_valid", "session_valid", "source_valid",
                "corporate_actions_clear", "point_in_time_valid"):
        if stage1.get(key) is not True:
            hard_failures.append(key + "_not_confirmed")
    if stage1.get("liquidity_pass") is not True:
        hard_failures.append("liquidity_gate_failed_or_unknown")
    if stage1.get("market_tradeable") is not True:
        hard_failures.append("market_gate_failed_or_unknown")
    if not refs:
        hard_failures.append("missing_stage_evidence_references")

    if hard_failures:
        reasons.extend(hard_failures)
    elif structure.get("distribution_confirmed") is True or structure.get("breakdown_confirmed") is True or structure.get("invalidation_triggered") is True:
        reasons.append("confirmed_distribution_breakdown_or_invalidation")
        if holding:
            action, subtype = "SELL", "SELL_NOW"
        else:
            action, subtype = "NO_TRADE", "AVOID_NEW_ENTRY"
    elif levels is None or not level_refs:
        reasons.append("evidence_backed_entry_stop_t1_and_level_references_required")
    elif coverage < 0.75:
        reasons.append("stage2_component_coverage_below_75_percent")
    elif score is None or score < 70:
        reasons.append("score_below_developing_setup_threshold")
    elif rr < 2:
        reasons.append("conservative_t1_reward_risk_below_2_to_1")
    elif not isinstance(structure.get("confirmed_by_horizon"), dict) or structure["confirmed_by_horizon"].get(horizon) is not True:
        reasons.append("horizon_specific_structure_confirmation_missing")
        if holding:
            action, subtype = "HOLD", "HOLD_WAIT"
        elif score >= 70:
            action, subtype = "NO_TRADE", "WAIT_FOR_CONFIRMATION"
    elif not isinstance(structure.get("entry_trigger"), dict) or structure["entry_trigger"].get(horizon) not in {
        "at_entry", "pullback", "breakout_confirmed", "retest_confirmed"
    }:
        reasons.append("entry_trigger_not_confirmed")
        if holding:
            action, subtype = "HOLD", "HOLD_WAIT"
        else:
            action, subtype = "NO_TRADE", "WAIT_FOR_CONFIRMATION"
    else:
        trigger = structure["entry_trigger"][horizon]
        action = "BUY"
        subtype = {
            "at_entry": "BUY_NOW",
            "pullback": "BUY_ON_PULLBACK",
            "breakout_confirmed": "BUY_ON_BREAKOUT_CONFIRMATION",
            "retest_confirmed": "BUY_AFTER_RETEST",
        }[trigger]
        reasons.append("all_stage1_and_horizon_trade_gates_passed")

    if action == "NO_TRADE" and holding and not hard_failures and not (
        structure.get("distribution_confirmed") is True
        or structure.get("breakdown_confirmed") is True
        or structure.get("invalidation_triggered") is True
    ):
        action, subtype = "HOLD", "HOLD_WITH_CAUTION"

    return {
        "symbol": str(symbol).upper(),
        "horizon": horizon,
        "horizon_definition": HORIZONS[horizon],
        "action": action,
        "subtype": subtype,
        "score": score,
        "score_coverage": coverage,
        "component_scores": accepted,
        "missing_components": missing,
        "rating": rating,
        "data_quality": quality,
        "confidence": "LOW" if hard_failures or coverage < 0.75 or action == "NO_TRADE" else (
            "HIGH" if quality == "HIGH" and coverage == 1 and len(refs) >= 3 and len(level_refs) >= 1 else "MEDIUM"
        ),
        "entry_zone": (
            {"low": levels["entry_low"], "high": levels["entry_high"]}
            if levels else None
        ),
        "add_on_zone": plan.get("add_on_zone"),
        "exit_zone": plan.get("exit_zone"),
        "stop_loss": levels["stop_loss"] if levels else None,
        "targets": levels["targets"] if levels else {"t1": None, "t2": None, "t3": None},
        "risk_percent": levels["risk_percent"] if levels else None,
        "reward_risk": rr,
        "invalidation": plan.get("invalidation"),
        "buy_side_liquidity": plan.get("buy_side_liquidity", []),
        "sell_side_liquidity": plan.get("sell_side_liquidity", []),
        "support": plan.get("support", []),
        "resistance": plan.get("resistance", []),
        "evidence_refs": refs,
        "level_evidence_refs": level_refs,
        "reasons": reasons,
        "methodology_version": "3.1-stage3-alpha1",
        "decision_status": "research_only_not_order_authorization",
    }


def evaluate_all_horizons(symbol, stage1, stage2, plans, evidence_refs=None,
                          holding=False):
    """Evaluate horizons independently; never reuse one horizon's trigger."""
    plans = plans if isinstance(plans, dict) else {}
    return {
        horizon: evaluate_horizon(
            symbol, horizon, stage1, stage2, plans.get(horizon),
            evidence_refs=evidence_refs, holding=holding,
        )
        for horizon in HORIZONS
    }

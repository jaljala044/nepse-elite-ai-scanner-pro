"""Conservative signal-path outcome measurement from verified daily OHLCV.

These are price-reference observations, never exchange fills or executable returns.
Same-session stop/target ambiguity is resolved against the strategy (stop first).
"""
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from .scanner import quality_errors
from .scanner_eligibility import assess, REVIEWED_ROWS

HORIZON_SESSIONS = {"t_plus_2": 5, "swing": 20, "positional": 126, "investment": 504}
KATHMANDU = ZoneInfo("Asia/Kathmandu")


def _d(value, name):
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"invalid_{name}") from None
    if not out.is_finite():
        raise ValueError(f"invalid_{name}")
    return out


def evaluate_signal_path(signal, rows, verified_sessions, *, evaluation_date, reviewed=None):
    """Evaluate entry/stop/target references without claiming fills.

    signal is the immutable record created by signal_tracking.freeze_signal.
    details must include a horizon plan with entry, stop and optional T1-T3.
    """
    reviewed = REVIEWED_ROWS if reviewed is None else reviewed
    if not isinstance(signal, dict) or signal.get("classification") != "research_only":
        raise ValueError("research_only_signal_required")
    if signal.get("action") != "BUY":
        return {"status": "not_applicable", "classification": "research_reference_not_execution",
                "reason": "only_buy_research_signals_have_long_price_path"}
    horizon = signal.get("horizon")
    if horizon not in HORIZON_SESSIONS:
        raise ValueError("unsupported_horizon")
    try:
        decision = datetime.fromisoformat(signal["decision_time"].replace("Z", "+00:00"))
        if decision.tzinfo is None or decision.utcoffset() is None:
            raise ValueError()
        decision_day = date.fromisoformat(str(signal.get("details", {}).get("decision_date", decision.date())))
        end = date.fromisoformat(str(evaluation_date))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("invalid_signal_decision_time_or_date") from None
    if end < decision_day:
        raise ValueError("evaluation_date_before_decision")
    if not isinstance(verified_sessions, list) or not verified_sessions:
        return {"status": "data_unavailable", "classification": "research_reference_not_execution",
                "reason": "verified_session_calendar_missing"}
    sessions = sorted({date.fromisoformat(str(x)) for x in verified_sessions})
    if decision_day not in sessions:
        return {"status": "data_unavailable", "classification": "research_reference_not_execution",
                "reason": "decision_session_not_verified"}
    if not isinstance(rows, list) or quality_errors(rows):
        return {"status": "data_unavailable", "classification": "research_reference_not_execution",
                "reason": "ohlcv_missing_or_invalid"}
    by_day = {date.fromisoformat(str(r["date"])): r for r in rows}
    if decision_day not in by_day:
        return {"status": "data_unavailable", "classification": "research_reference_not_execution",
                "reason": "decision_bar_missing"}
    future = [d for d in sessions if decision_day < d <= end]
    window = future[:HORIZON_SESSIONS[horizon]]
    if not window:
        return {"status": "awaiting_followup", "classification": "research_reference_not_execution",
                "reason": "no_post_signal_sessions"}
    if any(d not in by_day for d in window):
        return {"status": "data_incomplete", "classification": "research_reference_not_execution",
                "reason": "verified_session_bar_missing",
                "missing_sessions": [d.isoformat() for d in window if d not in by_day]}
    cutoff = datetime.combine(end, time.max, KATHMANDU).isoformat()
    observed_rows = [by_day[d] for d in window]
    errors = assess(signal["symbol"], [by_day[decision_day], *observed_rows], cutoff, reviewed)
    if errors:
        return {"status": "evidence_unverified", "classification": "research_reference_not_execution",
                "reason_codes": errors}
    details = signal.get("details") or {}
    plan = details.get("plan") or details
    entry = _d(plan.get("entry"), "entry")
    stop = _d(plan.get("stop"), "stop")
    targets_raw = plan.get("targets", [])
    if entry <= 0 or stop <= 0 or stop >= entry or not isinstance(targets_raw, list):
        raise ValueError("invalid_signal_price_geometry")
    targets = []
    for item in targets_raw[:3]:
        value = item.get("price") if isinstance(item, dict) else item
        target = _d(value, "target")
        if target <= entry:
            raise ValueError("invalid_signal_target")
        targets.append(target)
    entered = False
    entry_date = None
    exit_reference = None
    exit_date = None
    exit_reason = None
    target_hits = []
    ambiguous_sessions = []
    for d in window:
        bar = by_day[d]
        op, hi, lo, close = (_d(bar[k], k) for k in ("open", "high", "low", "close"))
        if not entered:
            if lo <= entry <= hi or op <= entry:
                entered = True
                entry_date = d
            else:
                continue
        stop_touched = lo <= stop
        newly_hit = [i + 1 for i, target in enumerate(targets) if hi >= target and i + 1 not in target_hits]
        if stop_touched and newly_hit:
            ambiguous_sessions.append(d.isoformat())
            exit_reference = min(op, stop)
            exit_date = d
            exit_reason = "stop_target_same_session_conservative_stop_first"
            break
        if stop_touched:
            exit_reference = min(op, stop)
            exit_date = d
            exit_reason = "stop_reference_touched"
            break
        target_hits.extend(newly_hit)
    last_close = _d(by_day[window[-1]]["close"], "last_close")
    mark = exit_reference if exit_reference is not None else (last_close if entered else None)
    return_pct = None if not entered else str((mark / entry - 1) * 100)
    return {"status": "observed" if len(window) == HORIZON_SESSIONS[horizon] or end >= window[-1] else "partial",
            "classification": "research_reference_not_execution",
            "signal_id": __import__("hashlib").sha256(str(signal).encode()).hexdigest(),
            "symbol": signal["symbol"], "horizon": horizon,
            "decision_date": decision_day.isoformat(), "evaluation_date": end.isoformat(),
            "sessions_observed": len(window), "entry_reference": str(entry),
            "entry_touched": entered, "entry_reference_date": entry_date.isoformat() if entry_date else None,
            "stop_reference": str(stop), "stop_touched": exit_reason is not None,
            "exit_reference": str(exit_reference) if exit_reference is not None else None,
            "exit_reference_date": exit_date.isoformat() if exit_date else None,
            "exit_reason": exit_reason, "targets_touched": [f"T{x}" for x in target_hits],
            "ambiguous_sessions": ambiguous_sessions, "mark_close": str(last_close),
            "reference_return_pct": return_pct,
            "limitations": ["OHLCV price touches are not verified orders or fills",
                            "Daily bars cannot establish intraday event order; ambiguous stop/target bars use stop-first",
                            "No fees, slippage, circuit-limit execution or market impact deducted"]}

"""Point-in-time panel readiness gate for the bounded NEPSE lifecycle pilot."""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Iterable, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str): raise ValueError(f"{field} must be timezone-aware ISO timestamp")
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"{field} must be timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise ValueError(f"{field} must be timezone-aware")
    return parsed

def build_lifecycle_panel_readiness(*, cohort_symbols: Iterable[str], security_master: Iterable[Mapping[str, object]], expected_sessions: Iterable[Mapping[str, object]], bars: Iterable[Mapping[str, object]], corporate_action_status: Mapping[str, object], decision_cutoff: str) -> dict:
    """Check identity, calendar, OHLCV and corporate-action prerequisites."""
    cutoff = _timestamp(decision_cutoff, "decision_cutoff")
    symbols = list(cohort_symbols)
    if not symbols or len(symbols) != len(set(symbols)): raise ValueError("cohort_symbols must be nonempty and unique")
    identities, identity_errors = {}, []
    for row in security_master:
        symbol, sid = str(row.get("symbol", "")), str(row.get("security_id", ""))
        if symbol not in symbols: continue
        if not sid or symbol in identities:
            identity_errors.append({"symbol": symbol, "reason": "missing_or_duplicate_security_identity"}); continue
        try:
            start = date.fromisoformat(str(row.get("effective_from", "")))
            end = date.fromisoformat(str(row["effective_to"])) if row.get("effective_to") else None
        except ValueError:
            identity_errors.append({"symbol": symbol, "reason": "invalid_identity_effective_dates"}); continue
        if end and end < start:
            identity_errors.append({"symbol": symbol, "reason": "identity_effective_interval_inverted"}); continue
        identities[symbol] = {"security_id": sid, "effective_from": start, "effective_to": end}
    for symbol in symbols:
        if symbol not in identities and not any(x["symbol"] == symbol for x in identity_errors):
            identity_errors.append({"symbol": symbol, "reason": "security_identity_missing"})
    session_keys, session_errors = set(), []
    for row in expected_sessions:
        try:
            day = date.fromisoformat(str(row.get("session_date", "")))
            available = _timestamp(row.get("available_at"), "session.available_at")
        except ValueError:
            session_errors.append({"session_date": row.get("session_date"), "reason": "invalid_session_evidence"}); continue
        if available > cutoff or row.get("status") != "confirmed_open" or not str(row.get("evidence_id", "")).strip():
            session_errors.append({"session_date": day.isoformat(), "reason": "session_not_point_in_time_verified_open"}); continue
        if day in session_keys: session_errors.append({"session_date": day.isoformat(), "reason": "duplicate_expected_session"})
        session_keys.add(day)
    bar_keys, bar_errors, accepted_bars = set(), [], 0
    for row in bars:
        symbol = str(row.get("symbol", ""))
        try:
            day = date.fromisoformat(str(row.get("session_date", "")))
            available = _timestamp(row.get("available_at"), "bar.available_at")
            opn, high, low, close = [float(row.get(k)) for k in ("open", "high", "low", "close")]
            volume = int(row.get("volume"))
        except (ValueError, TypeError, OverflowError):
            bar_errors.append({"symbol": symbol or None, "reason": "invalid_bar_fields"}); continue
        key = (symbol, day)
        if key in bar_keys:
            bar_errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "duplicate_symbol_session_bar"}); continue
        bar_keys.add(key)
        reason = None
        if symbol not in identities: reason = "bar_without_verified_identity"
        elif day < identities[symbol]["effective_from"] or (identities[symbol]["effective_to"] and day > identities[symbol]["effective_to"]): reason = "bar_outside_identity_lifecycle"
        elif day not in session_keys: reason = "bar_not_on_verified_open_session"
        elif available > cutoff: reason = "bar_after_decision_cutoff"
        elif not isinstance(row.get("raw_sha256"), str) or not _SHA256.fullmatch(row["raw_sha256"]): reason = "invalid_raw_sha256"
        elif min(opn, high, low, close) <= 0 or low > min(opn, close) or high < max(opn, close) or volume < 0: reason = "ohlcv_sanity_failed"
        if reason: bar_errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": reason})
        else: accepted_bars += 1
    missing = [{"symbol": s, "session_date": d.isoformat()} for s in symbols for d in sorted(session_keys) if s in identities and d >= identities[s]["effective_from"] and (identities[s]["effective_to"] is None or d <= identities[s]["effective_to"]) and (s, d) not in bar_keys]
    actions_valid = corporate_action_status.get("status") == "validated_for_research"
    actions_clean = actions_valid and not corporate_action_status.get("withheld_events") and not corporate_action_status.get("rejected_events")
    complete = not identity_errors and not session_errors and not bar_errors and not missing and actions_clean
    return {"status": "READY_FOR_BOUNDED_RESEARCH" if complete else "BLOCKED", "cohort_count": len(symbols), "verified_identity_count": len(identities), "verified_session_count": len(session_keys), "accepted_bar_count": accepted_bars, "identity_errors": identity_errors, "session_errors": session_errors, "bar_errors": bar_errors, "missing_symbol_sessions": missing, "corporate_actions": "validated_clean" if actions_clean else "missing_or_unreconciled", "coverage_pct": 100.0 if complete else None, "canonical_promotion_allowed": False, "backtest_admission_allowed": False, "production_enabled": False, "limitations": ["READY is only a bounded research assembly gate, not market-wide representativeness.", "Expected sessions must be evidence-backed; weekdays are never inferred.", "Corporate-action status is an externally supplied reconciliation report."]}

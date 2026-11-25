"""OHLCV ingestion gate joining parsed rows to dated universe/session evidence."""
from __future__ import annotations

from datetime import date, datetime, timezone
from app.ohlcv_csv_adapter import OhlcvCsvMapping, parse_ohlcv_csv
from app.session_evidence import resolve_session_state


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("availability timestamps must be ISO-8601 strings")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("availability timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def run_ohlcv_evidence_pipeline(payload: bytes, *, source_id: str,
                                mapping: OhlcvCsvMapping,
                                instrument_lifecycle: list[dict],
                                session_evidence: list,
                                decision_time: str,
                                availability_by_key: dict | None = None) -> dict:
    """Annotate each row; unknown membership/calendar/PIT state remains quarantined."""
    cutoff = _utc(decision_time)
    parsed = parse_ohlcv_csv(payload, source_id=source_id, mapping=mapping)
    by_symbol = {}
    for instrument in instrument_lifecycle:
        symbol = str(instrument.get("symbol", "")).strip().upper()
        if symbol:
            by_symbol.setdefault(symbol, []).append(instrument)

    output = []
    counts = {"eligible_for_review": 0, "quarantined": 0}
    for row in parsed["rows"]:
        symbol, session = row["symbol"], date.fromisoformat(row["session_date"])
        candidates = []
        for instrument in by_symbol.get(symbol, []):
            try:
                start = date.fromisoformat(instrument["valid_from"])
                end = date.fromisoformat(instrument["valid_to"]) if instrument.get("valid_to") else None
            except (KeyError, ValueError, TypeError):
                continue
            if start <= session and (end is None or session <= end):
                candidates.append(instrument)
        reasons = []
        if len(candidates) != 1:
            reasons.append("security_identity_missing_or_ambiguous")
        elif not str(candidates[0].get("security_id", "")).strip():
            reasons.append("security_master_id_missing")
        elif str(candidates[0].get("status", "")).casefold() not in {"active", "listed", "trading"}:
            reasons.append("security_not_active_on_session_date")
        session_state = resolve_session_state(session, session_evidence, decision_time)
        if not session_state["is_confirmed_trading_session"]:
            reasons.append("exchange_session_not_primary_evidence_verified")
        key = f"{symbol}|{session.isoformat()}"
        available_at = (availability_by_key or {}).get(key)
        if available_at is None:
            reasons.append("source_available_at_unknown")
        else:
            try:
                if _utc(available_at) > cutoff:
                    reasons.append("row_not_available_at_decision_time")
            except (TypeError, ValueError):
                reasons.append("invalid_source_available_at")
        if row["exception_flags"]:
            reasons.extend(row["exception_flags"])
        enriched = {
            **row,
            "security_id": candidates[0].get("security_id") if len(candidates) == 1 else None,
            "session_evidence": {
                "status": session_state["status"],
                "session_state": session_state["session_state"],
                "evidence_ids": session_state["evidence_ids"],
            },
            "source_available_at": available_at,
            "point_in_time_status": "verified_as_of_decision" if available_at is not None
                and not any(x in reasons for x in ("source_available_at_unknown",
                    "row_not_available_at_decision_time", "invalid_source_available_at")) else "unknown_or_late",
            "row_status": "eligible_for_review" if not reasons else "quarantined",
            "quarantine_reasons": sorted(set(reasons)),
        }
        output.append(enriched)
        counts[enriched["row_status"]] += 1
    rejected_rows = [item for item in parsed["exceptions"] if item.get("status") == "rejected"]
    if parsed["input_rows"] != len(output) + len(rejected_rows):
        raise AssertionError("OHLCV parser row conservation failed")
    return {
        "source_id": source_id, "source_payload_sha256": parsed["source_payload_sha256"],
        "input_rows": parsed["input_rows"], "parsed_rows": parsed["parsed_rows"],
        "rows": output, "rejected_rows": rejected_rows,
        "counts": {**counts, "parser_rejected": len(rejected_rows)},
        "row_conservation_passed": True,
        "promotion_allowed": False,
        "policy": "require_dated_security_primary_session_and_point_in_time_evidence_retain_parser_rejections",
    }

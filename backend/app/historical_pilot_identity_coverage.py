"""Effective-dated identity/action evidence and bounded OHLCV coverage pilot.

This module validates supplied evidence; it does not discover dates, resolve
ambiguous identities, fetch publishers, or promote a canonical price series.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_IDENTITY_TYPES = {"equity", "mutual_fund", "debenture", "bond", "promoter_share", "other"}
_ACTION_TYPES = {"bonus", "rights", "split", "reverse_split", "cash_dividend", "merger", "demerger", "symbol_change", "delisting"}


def _day(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field}_invalid")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    return parsed


def _digest(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def validate_effective_dated_security_identity(
    *, identity_records: list[Mapping[str, Any]], decision_cutoff: str,
) -> dict:
    """Validate symbol/security-ID intervals and primary evidence provenance."""
    cutoff = _timestamp(decision_cutoff, "decision_cutoff")
    errors: list[dict] = []
    accepted: list[dict] = []
    for index, row in enumerate(identity_records):
        if not isinstance(row, Mapping):
            errors.append({"index": index, "reason": "identity_record_not_mapping"})
            continue
        try:
            start = _day(row.get("effective_from"), "effective_from")
            end = _day(row["effective_to"], "effective_to") if row.get("effective_to") else None
            available = _timestamp(row.get("available_at"), "available_at")
            observed = _timestamp(row.get("observed_at"), "observed_at")
        except (ValueError, KeyError) as exc:
            errors.append({"index": index, "reason": str(exc)})
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        security_id = str(row.get("security_id", "")).strip()
        instrument_type = str(row.get("instrument_type", "")).strip().lower()
        source_id = str(row.get("source_id", "")).strip()
        publisher_id = str(row.get("publisher_id", "")).strip()
        digest = row.get("evidence_sha256")
        authority = row.get("authority")
        if not symbol or not security_id or not source_id or not publisher_id:
            errors.append({"index": index, "reason": "identity_key_or_provenance_missing"})
        if instrument_type not in _IDENTITY_TYPES:
            errors.append({"index": index, "reason": "instrument_type_invalid"})
        if end and end < start:
            errors.append({"index": index, "reason": "identity_interval_inverted"})
        if available > cutoff or observed > cutoff:
            errors.append({"index": index, "reason": "identity_evidence_after_decision_cutoff"})
        if not _digest(digest):
            errors.append({"index": index, "reason": "identity_evidence_hash_invalid"})
        if authority not in {"exchange_primary", "depository_primary", "third_party"}:
            errors.append({"index": index, "reason": "identity_authority_invalid"})
        if authority == "third_party" and row.get("publisher_independence_reviewed") is not True:
            errors.append({"index": index, "reason": "third_party_independence_not_reviewed"})
        if (symbol and security_id and instrument_type in _IDENTITY_TYPES and source_id and publisher_id
                and _digest(digest) and authority in {"exchange_primary", "depository_primary", "third_party"}
                and (not end or end >= start) and available <= cutoff and observed <= cutoff):
            accepted.append({
                "symbol": symbol, "security_id": security_id, "instrument_type": instrument_type,
                "effective_from": start.isoformat(), "effective_to": end.isoformat() if end else None,
                "source_id": source_id, "publisher_id": publisher_id, "authority": authority,
                "evidence_sha256": digest.lower(),
            })

    def overlaps(a: dict, b: dict) -> bool:
        a_end = date.fromisoformat(a["effective_to"]) if a["effective_to"] else date.max
        b_end = date.fromisoformat(b["effective_to"]) if b["effective_to"] else date.max
        return date.fromisoformat(a["effective_from"]) <= b_end and date.fromisoformat(b["effective_from"]) <= a_end

    for i, left in enumerate(accepted):
        for right in accepted[i + 1:]:
            if left["source_id"] == right["source_id"] and left["evidence_sha256"] == right["evidence_sha256"]:
                continue
            if left["security_id"] == right["security_id"] and left["symbol"] != right["symbol"] and overlaps(left, right):
                errors.append({"reason": "security_id_maps_to_multiple_symbols_in_overlapping_interval",
                               "security_id": left["security_id"], "symbols": sorted([left["symbol"], right["symbol"]])})
            if left["symbol"] == right["symbol"] and left["security_id"] != right["security_id"] and overlaps(left, right):
                errors.append({"reason": "symbol_maps_to_multiple_security_ids_in_overlapping_interval",
                               "symbol": left["symbol"], "security_ids": sorted([left["security_id"], right["security_id"]])})
            if left["symbol"] == right["symbol"] and left["security_id"] == right["security_id"] and left["instrument_type"] != right["instrument_type"] and overlaps(left, right):
                errors.append({"reason": "instrument_type_conflict_in_overlapping_interval", "symbol": left["symbol"]})
    distinct_primary = {x["publisher_id"] for x in accepted if x["authority"] in {"exchange_primary", "depository_primary"}}
    if not distinct_primary:
        errors.append({"reason": "no_primary_identity_evidence"})
    canonical = _canonical_hash({"accepted": accepted, "errors": errors})
    return {
        "status": "IDENTITY_EVIDENCE_VALIDATED" if accepted and not errors else "IDENTITY_EVIDENCE_BLOCKED",
        "accepted_record_count": len(accepted), "accepted_records": accepted,
        "primary_publisher_count": len(distinct_primary), "errors": errors,
        "identity_sha256": canonical, "historical_identity_fully_verified": bool(accepted and not errors and distinct_primary),
        "canonical_universe_promotion_allowed": False,
    }


def validate_corporate_action_evidence(
    *, action_records: list[Mapping[str, Any]], decision_cutoff: str,
) -> dict:
    """Require dated, two-publisher corroboration and a primary authority for each action."""
    cutoff = _timestamp(decision_cutoff, "decision_cutoff")
    errors: list[dict] = []
    groups: dict[str, list[dict]] = defaultdict(list)
    for index, row in enumerate(action_records):
        if not isinstance(row, Mapping):
            errors.append({"index": index, "reason": "action_record_not_mapping"})
            continue
        try:
            effective = _day(row.get("effective_date"), "effective_date")
            announced = _timestamp(row.get("available_at"), "available_at")
        except ValueError as exc:
            errors.append({"index": index, "reason": str(exc)})
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        action_type = str(row.get("action_type", "")).strip().lower()
        source_id = str(row.get("source_id", "")).strip()
        publisher_id = str(row.get("publisher_id", "")).strip()
        authority = row.get("authority")
        event_id = str(row.get("event_id", "")).strip()
        digest = row.get("evidence_sha256")
        if not symbol or not event_id or not source_id or not publisher_id:
            errors.append({"index": index, "reason": "action_identity_or_provenance_missing"})
        if action_type not in _ACTION_TYPES:
            errors.append({"index": index, "reason": "action_type_invalid"})
        if announced > cutoff:
            errors.append({"index": index, "reason": "action_evidence_after_decision_cutoff"})
        if authority not in {"exchange_primary", "depository_primary", "third_party"}:
            errors.append({"index": index, "reason": "action_authority_invalid"})
        if not _digest(digest):
            errors.append({"index": index, "reason": "action_evidence_hash_invalid"})
        ratio = row.get("adjustment_factor")
        if action_type in {"bonus", "rights", "split", "reverse_split"}:
            try:
                factor = Decimal(str(ratio))
                if not factor.is_finite() or factor <= 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                errors.append({"index": index, "reason": "price_adjustment_factor_invalid"})
        else:
            factor = None
        if (symbol and event_id and source_id and publisher_id and action_type in _ACTION_TYPES
                and announced <= cutoff and authority in {"exchange_primary", "depository_primary", "third_party"}
                and _digest(digest) and (action_type not in {"bonus", "rights", "split", "reverse_split"} or factor is not None)):
            groups[event_id].append({
                "symbol": symbol, "action_type": action_type, "effective_date": effective.isoformat(),
                "source_id": source_id, "publisher_id": publisher_id, "authority": authority,
                "evidence_sha256": digest.lower(), "adjustment_factor": str(factor) if factor is not None else None,
            })
    accepted_events = []
    for event_id, records in sorted(groups.items()):
        publishers = {x["publisher_id"] for x in records}
        primary = {x["publisher_id"] for x in records if x["authority"] in {"exchange_primary", "depository_primary"}}
        facts = {(x["symbol"], x["action_type"], x["effective_date"], x["adjustment_factor"]) for x in records}
        if len(publishers) < 2 or not primary:
            errors.append({"event_id": event_id, "reason": "action_requires_two_publishers_including_primary"})
        if len(facts) != 1:
            errors.append({"event_id": event_id, "reason": "action_sources_disagree_on_event_facts"})
        if len(publishers) >= 2 and primary and len(facts) == 1:
            accepted_events.append({"event_id": event_id, **records[0], "publisher_count": len(publishers)})
    canonical = _canonical_hash({"events": accepted_events, "errors": errors})
    return {
        "status": "CORPORATE_ACTION_EVIDENCE_VALIDATED" if accepted_events and not errors else "CORPORATE_ACTION_EVIDENCE_BLOCKED",
        "accepted_event_count": len(accepted_events), "accepted_events": accepted_events,
        "errors": errors, "corporate_action_sha256": canonical,
        "adjusted_price_admission_allowed": False,
    }


def build_bounded_ohlcv_coverage_pilot(
    *, records: list[Mapping[str, Any]], expected_sessions: list[str],
    identity_report: Mapping[str, Any], corporate_action_report: Mapping[str, Any],
    source_requirements: Mapping[str, Any], close_tolerance: str = "0.01",
) -> dict:
    """Compare source-specific coverage against an explicitly verified session/universe grid."""
    errors: list[dict] = []
    if identity_report.get("status") != "IDENTITY_EVIDENCE_VALIDATED":
        errors.append({"reason": "effective_dated_identity_not_validated"})
    if corporate_action_report.get("status") != "CORPORATE_ACTION_EVIDENCE_VALIDATED":
        errors.append({"reason": "corporate_action_evidence_not_validated"})
    if source_requirements.get("official_calendar_verified") is not True:
        errors.append({"reason": "official_calendar_not_verified"})
    if source_requirements.get("session_calendar_sha256") and not _digest(source_requirements.get("session_calendar_sha256")):
        errors.append({"reason": "session_calendar_hash_invalid"})
    if source_requirements.get("universe_manifest_verified") is not True:
        errors.append({"reason": "effective_dated_universe_not_verified"})
    if source_requirements.get("universe_manifest_sha256") and not _digest(source_requirements.get("universe_manifest_sha256")):
        errors.append({"reason": "universe_manifest_hash_invalid"})
    if not expected_sessions:
        errors.append({"reason": "verified_expected_sessions_missing"})
    if not identity_report.get("accepted_records"):
        errors.append({"reason": "identity_records_missing"})

    try:
        tolerance = Decimal(str(close_tolerance))
        if not tolerance.is_finite() or tolerance < 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        tolerance = Decimal("0")
        errors.append({"reason": "close_tolerance_invalid"})

    sessions = sorted({_day(x, "expected_session").isoformat() for x in expected_sessions})
    active_symbols = set()
    for identity in identity_report.get("accepted_records", []):
        start = date.fromisoformat(identity["effective_from"])
        end = date.fromisoformat(identity["effective_to"]) if identity.get("effective_to") else date.max
        if any(start <= date.fromisoformat(day) <= end for day in sessions) and identity["instrument_type"] == "equity":
            active_symbols.add(identity["symbol"])
    if not active_symbols:
        errors.append({"reason": "no_effective_equity_symbols_in_requested_window"})
    expected = {(day, symbol) for day in sessions for symbol in sorted(active_symbols)}
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    invalid_rows = []
    for index, row in enumerate(records):
        try:
            day = _day(row.get("session_date"), "session_date").isoformat()
            symbol = str(row.get("symbol", "")).strip().upper()
            source = str(row.get("source_id", "")).strip()
            close = Decimal(str(row.get("close")))
            if not symbol or not source or not close.is_finite() or close <= 0:
                raise ValueError("symbol/source missing or close invalid")
            if day not in sessions or symbol not in active_symbols:
                invalid_rows.append({"index": index, "reason": "row_outside_verified_session_or_equity_universe"})
                continue
            digest = row.get("raw_payload_sha256")
            if not _digest(digest):
                raise ValueError("raw_payload_sha256_invalid")
            grouped[(day, symbol, source)].append(row)
        except (ValueError, InvalidOperation, TypeError) as exc:
            invalid_rows.append({"index": index, "reason": str(exc)})
    if invalid_rows:
        errors.append({"reason": "invalid_or_out_of_scope_rows", "count": len(invalid_rows)})

    sources = sorted({key[2] for key in grouped})
    per_source = {}
    conflicts = []
    for source in sources:
        present, missing, duplicates = set(), [], []
        for key in sorted(expected):
            rows = grouped.get((key[0], key[1], source), [])
            if rows:
                present.add(key)
                if len(rows) > 1:
                    duplicates.append({"session_date": key[0], "symbol": key[1], "row_count": len(rows)})
            else:
                missing.append({"session_date": key[0], "symbol": key[1]})
        per_source[source] = {
            "covered_keys": len(present), "expected_keys": len(expected),
            "coverage_ratio": str(Decimal(len(present)) / Decimal(len(expected))) if expected else "0",
            "missing_keys": missing, "duplicate_keys": duplicates,
        }
    for day, symbol in sorted(expected):
        observed = []
        for source in sources:
            rows = grouped.get((day, symbol, source), [])
            for row in rows:
                try:
                    close = Decimal(str(row["close"]))
                    observed.append({"source_id": source, "close": close})
                except (KeyError, InvalidOperation, TypeError):
                    errors.append({"reason": "close_parse_error", "session_date": day, "symbol": symbol})
        if len({x["source_id"] for x in observed}) > 1 and observed:
            low = min(x["close"] for x in observed)
            high = max(x["close"] for x in observed)
            if high - low > tolerance:
                conflicts.append({
                    "session_date": day, "symbol": symbol,
                    "observations": [{"source_id": x["source_id"], "close": str(x["close"])} for x in observed],
                    "absolute_close_spread": str(high - low),
                })
    union_covered = sum(1 for key in expected if any(grouped.get((key[0], key[1], source)) for source in sources))
    summary = {
        "expected_sessions": sessions, "expected_session_count": len(sessions),
        "effective_equity_symbol_count": len(active_symbols), "expected_symbol_session_keys": len(expected),
        "source_reports": per_source, "union_covered_keys": union_covered,
        "union_missing_keys": len(expected) - union_covered,
        "cross_source_close_conflict_count": len(conflicts), "cross_source_conflicts": conflicts,
        "invalid_row_count": len(invalid_rows), "invalid_rows": invalid_rows,
        "identity_sha256": identity_report.get("identity_sha256"),
        "corporate_action_sha256": corporate_action_report.get("corporate_action_sha256"),
        "source_requirements": dict(source_requirements),
    }
    fingerprint = _canonical_hash(summary)
    return {
        "status": "COVERAGE_PILOT_REVIEW_READY" if not errors and not conflicts and union_covered == len(expected) else "COVERAGE_PILOT_BLOCKED",
        "errors": errors, "summary": summary, "coverage_pilot_sha256": fingerprint,
        "all_source_conflicts_resolved": not conflicts,
        "canonical_promotion_allowed": False, "scanner_replay_allowed": False,
        "limitations": [
            "Coverage is only as reliable as the explicitly supplied session calendar and identity evidence.",
            "Rows are compared source-by-source; source values are never blended or auto-selected.",
            "A coverage-ready pilot remains review-only until a separate human admission and execution-realism review.",
        ],
    }

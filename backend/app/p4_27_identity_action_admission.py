"""Steps 88-89: point-in-time identity resolution and action reconciliation.

These gates consume operator-supplied, hashed evidence. They do not fetch data,
infer security IDs, calculate adjustment factors, or mutate historical prices.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_ACTION_TYPES = {
    "bonus", "rights", "split", "reverse_split", "cash_dividend",
    "stock_dividend", "merger", "demerger",
}


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_missing_or_invalid")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return result


def _day(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field}_missing_or_invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc


def _valid_hash(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _overlap(a_start: date, a_end: date | None, b_start: date, b_end: date | None) -> bool:
    # Intervals are inclusive. None means still active/open-ended.
    return (a_end is None or b_start <= a_end) and (b_end is None or a_start <= b_end)


def resolve_effective_dated_identities(
    *, records: list[dict[str, Any]], required_symbols: list[str],
    archive_report: dict[str, Any], decision_cutoff: str,
) -> dict[str, Any]:
    """Resolve symbol/security identity intervals only from archived primary evidence."""
    cutoff = _timestamp(decision_cutoff, "decision_cutoff")
    if archive_report.get("status") != "PRIMARY_NOTICE_ARCHIVE_VERIFIED":
        return {
            "status": "IDENTITY_INTERVALS_BLOCKED", "accepted_interval_count": 0,
            "accepted_intervals": [], "missing_symbols": sorted({x.strip().upper() for x in required_symbols}),
            "errors": [{"reason": "primary_notice_archive_not_fully_verified"}],
            "historical_universe_join_allowed": False,
            "note": "A fully verified primary archive is required before identity resolution.",
        }
    docs = {x.get("event_id"): x for x in archive_report.get("verified_documents", [])}
    accepted: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for index, row in enumerate(records):
        symbol = str(row.get("symbol", "")).strip().upper()
        security_id = str(row.get("security_id", "")).strip()
        instrument = str(row.get("instrument_class", "")).strip().lower()
        event_id = str(row.get("event_id", "")).strip()
        try:
            if not symbol or not security_id or not instrument:
                raise ValueError("symbol_security_id_or_instrument_class_missing")
            start = _day(row.get("effective_from"), "effective_from")
            end_value = row.get("effective_to")
            end = _day(end_value, "effective_to") if end_value not in (None, "") else None
            if end is not None and end < start:
                raise ValueError("identity_interval_end_before_start")
            available = _timestamp(row.get("available_at"), "available_at")
            if available > cutoff:
                raise ValueError("identity_evidence_after_decision_cutoff")
            if row.get("source_tier") != "primary_nepse_or_cdsc":
                raise ValueError("identity_source_not_primary")
            doc = docs.get(event_id)
            if not doc:
                raise ValueError("identity_primary_archive_document_missing")
            if str(row.get("publisher_id", "")).strip() != str(doc.get("publisher_id", "")).strip():
                raise ValueError("identity_publisher_mismatch")
            if str(row.get("evidence_sha256", "")).lower() != str(doc.get("sha256", "")).lower():
                raise ValueError("identity_hash_not_bound_to_archived_document")
            doc_available = _timestamp(doc.get("available_at"), "document_available_at")
            if available < doc_available:
                raise ValueError("identity_available_before_linked_document")
            reviewer = str(row.get("reviewer_id", "")).strip()
            if row.get("review_status") != "approved" or not reviewer:
                raise ValueError("identity_independent_review_missing")
            if reviewer == str(row.get("publisher_id", "")).strip():
                raise ValueError("identity_reviewer_not_independent")
            key = (symbol, security_id, instrument, start.isoformat())
            if key in seen:
                raise ValueError("duplicate_identity_interval")
            seen.add(key)
            accepted.append({
                "symbol": symbol, "security_id": security_id,
                "instrument_class": instrument, "effective_from": start.isoformat(),
                "effective_to": end.isoformat() if end else None,
                "available_at": available.isoformat(), "event_id": event_id,
                "publisher_id": row["publisher_id"], "evidence_sha256": doc["sha256"],
                "reviewer_id": reviewer,
            })
        except (ValueError, KeyError) as exc:
            errors.append({"index": index, "symbol": symbol, "reason": str(exc)})

    # A symbol/class or stable security ID cannot map to overlapping identities.
    for i, left in enumerate(accepted):
        left_start = date.fromisoformat(left["effective_from"])
        left_end = date.fromisoformat(left["effective_to"]) if left["effective_to"] else None
        for right in accepted[i + 1:]:
            right_start = date.fromisoformat(right["effective_from"])
            right_end = date.fromisoformat(right["effective_to"]) if right["effective_to"] else None
            same_symbol_class = (
                left["symbol"] == right["symbol"]
                and left["instrument_class"] == right["instrument_class"]
            )
            same_security_id = left["security_id"] == right["security_id"]
            if (same_symbol_class or same_security_id) and _overlap(
                left_start, left_end, right_start, right_end
            ):
                errors.append({
                    "reason": "overlapping_effective_identity_intervals",
                    "left": [left["symbol"], left["security_id"]],
                    "right": [right["symbol"], right["security_id"]],
                })

    resolved_symbols = {x["symbol"] for x in accepted}
    missing = sorted({x.strip().upper() for x in required_symbols} - resolved_symbols)
    if missing:
        errors.append({"reason": "required_identity_symbols_unresolved", "symbols": missing})
    return {
        "status": "IDENTITY_INTERVALS_REVIEWED" if accepted and not errors else "IDENTITY_INTERVALS_BLOCKED",
        "accepted_interval_count": len(accepted),
        "accepted_intervals": sorted(accepted, key=lambda x: (x["symbol"], x["effective_from"])),
        "missing_symbols": missing, "errors": errors,
        "historical_universe_join_allowed": False,
        "note": "Review-ready intervals still require a separately approved universe admission.",
    }


def reconcile_corporate_action_assertions(
    *, records: list[dict[str, Any]], decision_cutoff: str,
) -> dict[str, Any]:
    """Require independent primary/secondary agreement for each action event."""
    cutoff = _timestamp(decision_cutoff, "decision_cutoff")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors: list[dict[str, Any]] = []
    seen_sources: set[tuple[str, str, str]] = set()

    for index, row in enumerate(records):
        action_id = str(row.get("action_id", "")).strip()
        try:
            if not action_id:
                raise ValueError("action_id_missing")
            symbol = str(row.get("symbol", "")).strip().upper()
            security_id = str(row.get("security_id", "")).strip()
            action_type = str(row.get("action_type", "")).strip().lower()
            if not symbol or not security_id:
                raise ValueError("action_security_identity_missing")
            if action_type not in _ACTION_TYPES:
                raise ValueError("action_type_invalid")
            announced = _timestamp(row.get("announced_at"), "announced_at")
            available = _timestamp(row.get("available_at"), "available_at")
            ex_date = _day(row.get("ex_date"), "ex_date")
            if announced > cutoff or available > cutoff:
                raise ValueError("action_assertion_after_decision_cutoff")
            if available < announced:
                raise ValueError("action_available_before_announcement")
            if ex_date < announced.date():
                raise ValueError("ex_date_precedes_announcement")
            publisher = str(row.get("publisher_id", "")).strip()
            source_id = str(row.get("source_id", "")).strip()
            tier = str(row.get("source_tier", "")).strip()
            digest = row.get("evidence_sha256")
            if not publisher or not source_id or tier not in {
                "primary_nepse_or_cdsc", "independent_secondary"
            }:
                raise ValueError("action_source_provenance_invalid")
            if not _valid_hash(digest):
                raise ValueError("action_evidence_sha256_invalid")
            source_key = (action_id, publisher, source_id)
            if source_key in seen_sources:
                raise ValueError("duplicate_action_source_assertion")
            seen_sources.add(source_key)
            status = str(row.get("status", "")).strip().lower()
            if status not in {"announced", "confirmed", "cancelled", "rejected"}:
                raise ValueError("action_status_invalid")

            factor = None
            method = str(row.get("factor_methodology_id", "")).strip()
            if action_type in {"bonus", "rights", "split", "reverse_split", "stock_dividend"}:
                try:
                    factor = Decimal(str(row.get("adjustment_factor")))
                except (InvalidOperation, TypeError, ValueError):
                    raise ValueError("action_adjustment_factor_invalid") from None
                if not factor.is_finite() or factor <= 0:
                    raise ValueError("action_adjustment_factor_invalid")
                if not method:
                    raise ValueError("action_factor_methodology_missing")
            elif row.get("adjustment_factor") not in (None, "") or method:
                raise ValueError("cash_or_non_price_action_must_not_supply_price_factor")

            reviewer = str(row.get("reviewer_id", "")).strip()
            review = str(row.get("review_status", "")).strip().lower()
            if review != "approved" or not reviewer:
                raise ValueError("independent_action_review_missing")
            if reviewer == publisher:
                raise ValueError("action_reviewer_not_independent")

            groups[action_id].append({
                "action_id": action_id, "symbol": symbol, "security_id": security_id,
                "action_type": action_type, "announced_date": announced.date().isoformat(),
                "ex_date": ex_date.isoformat(), "status": status,
                "adjustment_factor": str(factor) if factor is not None else None,
                "factor_methodology_id": method or None, "publisher_id": publisher,
                "source_id": source_id, "source_tier": tier,
                "evidence_sha256": digest.lower(), "reviewer_id": reviewer,
                "available_at": available.isoformat(),
            })
        except (ValueError, KeyError) as exc:
            errors.append({"index": index, "action_id": action_id, "reason": str(exc)})

    reconciled: list[dict[str, Any]] = []
    for action_id, assertions in sorted(groups.items()):
        publishers = {x["publisher_id"] for x in assertions}
        primary = {x["publisher_id"] for x in assertions if x["source_tier"] == "primary_nepse_or_cdsc"}
        facts = {
            (x["symbol"], x["security_id"], x["action_type"], x["announced_date"],
             x["ex_date"], x["status"], x["adjustment_factor"], x["factor_methodology_id"])
            for x in assertions
        }
        if len(publishers) < 2 or not primary:
            errors.append({"action_id": action_id, "reason": "requires_two_publishers_including_primary"})
        if len(facts) != 1:
            errors.append({"action_id": action_id, "reason": "corporate_action_assertions_disagree"})
        if len({x["reviewer_id"] for x in assertions}) < 1:
            errors.append({"action_id": action_id, "reason": "independent_reviewer_missing"})
        if len(publishers) >= 2 and primary and len(facts) == 1:
            reconciled.append({
                "action_id": action_id, "assertions": assertions,
                "publisher_count": len(publishers),
                "reconciliation_status": "TWO_SOURCE_FACTS_AGREE",
            })

    return {
        "status": "ACTION_ASSERTIONS_RECONCILED" if reconciled and not errors else "ACTION_RECONCILIATION_BLOCKED",
        "reconciled_event_count": len(reconciled), "reconciled_events": reconciled,
        "errors": errors, "price_adjustment_admission_allowed": False,
        "note": "Agreement is evidence readiness only; adjustment requires separate corporate-action completeness, identity and policy approval.",
    }

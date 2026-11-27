"""Auditable coverage and exception dashboard for the bounded historical pilot."""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_date(value: object) -> date:
    if not isinstance(value, str):
        raise ValueError("date must be canonical YYYY-MM-DD text")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date must be canonical YYYY-MM-DD text")
    return parsed


def build_historical_pilot_quality_dashboard(
    *, cohort_symbols: Iterable[str], security_master: Iterable[Mapping[str, object]],
    expected_sessions: Iterable[Mapping[str, object]], panel_report: Mapping[str, object],
    reconciliation_report: Mapping[str, object], replay_preflight: Mapping[str, object],
    corporate_action_status: Mapping[str, object],
) -> dict:
    """Summarize supplied evidence; incomplete inputs can never look review-ready."""
    symbols, master, sessions = list(cohort_symbols), list(security_master), list(expected_sessions)
    if (not symbols or len(symbols) != len(set(symbols)) or
            any(not isinstance(s, str) or not s or s != s.strip() or s != s.upper() for s in symbols)):
        raise ValueError("cohort_symbols must be nonempty, unique, canonical uppercase strings")

    blockers: list[str] = []
    identity_errors: list[dict] = []
    by_symbol: dict[str, list[Mapping[str, object]]] = {s: [] for s in symbols}
    seen_security_ids: dict[str, str] = {}
    for index, item in enumerate(master):
        if not isinstance(item, Mapping):
            identity_errors.append({"index": index, "reason": "identity_row_not_mapping"})
            continue
        symbol = item.get("symbol")
        if symbol not in by_symbol:
            identity_errors.append({"index": index, "reason": "identity_symbol_invalid_or_outside_cohort"})
            continue
        by_symbol[symbol].append(item)

    valid_identity: dict[str, tuple[date, date | None, str]] = {}
    for symbol in symbols:
        records = by_symbol[symbol]
        if len(records) != 1:
            identity_errors.append({"symbol": symbol, "reason": "identity_missing" if not records else "duplicate_identity_rows", "count": len(records)})
            continue
        item = records[0]
        security_id = item.get("security_id")
        try:
            start = _canonical_date(item.get("effective_from"))
            end = _canonical_date(item.get("effective_to")) if item.get("effective_to") else None
            if end is not None and end < start:
                raise ValueError("effective interval inverted")
            if not isinstance(security_id, str) or not security_id.strip():
                raise ValueError("security_id missing")
            if security_id in seen_security_ids and seen_security_ids[security_id] != symbol:
                raise ValueError("security_id reused across cohort symbols")
            seen_security_ids[security_id] = symbol
            valid_identity[symbol] = (start, end, security_id)
        except (TypeError, ValueError):
            identity_errors.append({"symbol": symbol, "reason": "identity_fields_invalid"})

    if identity_errors:
        blockers.append("identity_coverage_incomplete_or_conflicted")

    session_errors: list[dict] = []
    open_days: set[str] = set()
    session_counts: dict[str, int] = {}
    for index, item in enumerate(sessions):
        if not isinstance(item, Mapping):
            session_errors.append({"index": index, "reason": "session_row_not_mapping"})
            continue
        try:
            day = _canonical_date(item.get("session_date")).isoformat()
        except (TypeError, ValueError):
            session_errors.append({"index": index, "reason": "session_date_invalid"})
            continue
        session_counts[day] = session_counts.get(day, 0) + 1
        if item.get("status") == "confirmed_open":
            evidence_id = item.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id.strip():
                session_errors.append({"session_date": day, "reason": "open_session_evidence_id_missing"})
            else:
                open_days.add(day)
        elif item.get("status") not in ("confirmed_closed", "unknown", "suspended"):
            session_errors.append({"session_date": day, "reason": "session_status_invalid"})
    duplicate_sessions = sorted(day for day, count in session_counts.items() if count > 1)
    if duplicate_sessions:
        session_errors.extend({"session_date": day, "reason": "duplicate_session_rows"} for day in duplicate_sessions)
    if not sessions or not open_days:
        session_errors.append({"reason": "expected_session_evidence_empty"})
    if session_errors:
        blockers.append("expected_session_evidence_incomplete_or_invalid")

    expected: set[tuple[str, str]] = set()
    for symbol, (start, end, _security_id) in valid_identity.items():
        for day_text in open_days:
            day = date.fromisoformat(day_text)
            if day >= start and (end is None or day <= end):
                expected.add((symbol, day_text))
    if not expected:
        blockers.append("expected_symbol_session_denominator_empty")

    rows_value = panel_report.get("panel_rows", [])
    rows = list(rows_value) if isinstance(rows_value, (list, tuple)) else []
    row_errors: list[dict] = []
    row_counts: dict[tuple[str, str], int] = {}
    observed: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            row_errors.append({"index": index, "reason": "panel_row_not_mapping"})
            continue
        symbol = row.get("symbol")
        try:
            day_text = _canonical_date(row.get("session_date")).isoformat()
        except (TypeError, ValueError):
            row_errors.append({"index": index, "reason": "panel_session_date_invalid"})
            continue
        if symbol not in symbols:
            row_errors.append({"index": index, "reason": "panel_symbol_invalid_or_outside_cohort"})
            continue
        key = (symbol, day_text)
        row_counts[key] = row_counts.get(key, 0) + 1
        observed.add(key)
    duplicate_panel_rows = [
        {"symbol": symbol, "session_date": day, "count": count}
        for (symbol, day), count in sorted(row_counts.items()) if count > 1
    ]
    if duplicate_panel_rows:
        row_errors.extend({"reason": "duplicate_panel_symbol_session", **item} for item in duplicate_panel_rows)

    missing = [{"symbol": s, "session_date": d} for s, d in sorted(expected - observed)]
    unexpected = [{"symbol": s, "session_date": d} for s, d in sorted(observed - expected)]
    conflict_rows = list(panel_report.get("conflicts", []))
    ingestion_errors = list(panel_report.get("ingestion_errors", []))
    insufficient = list(panel_report.get("insufficient_source_coverage", []))
    if row_errors:
        blockers.append("panel_rows_malformed_or_duplicated")
    if missing or unexpected or conflict_rows or ingestion_errors or insufficient:
        blockers.append("panel_coverage_or_integrity_exceptions")

    capture_missing = list(reconciliation_report.get("missing_capture_keys", []))
    capture_failed = list(reconciliation_report.get("failed_capture_keys", []))
    duplicate_captures = list(reconciliation_report.get("duplicate_capture_ids", []))
    first_trade = reconciliation_report.get("first_trade_report", {})
    corporate_exceptions = list(corporate_action_status.get("withheld_events", [])) + list(corporate_action_status.get("rejected_events", []))
    if panel_report.get("status") != "PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH":
        blockers.append("panel_not_assembled")
    if reconciliation_report.get("status") != "SOURCE_EVIDENCE_RECONCILED":
        blockers.append("source_reconciliation_incomplete")
    if replay_preflight.get("status") != "BOUNDED_PILOT_REPLAY_PREFLIGHT_READY":
        blockers.append("replay_preflight_blocked")
    manifest = replay_preflight.get("dataset_manifest")
    manifest_sha = manifest.get("sha256") if isinstance(manifest, Mapping) else None
    if not isinstance(manifest_sha, str) or not _SHA256.fullmatch(manifest_sha):
        blockers.append("dataset_manifest_sha256_invalid")
    if corporate_action_status.get("status") != "validated_for_research" or corporate_exceptions:
        blockers.append("corporate_action_evidence_incomplete")
    if capture_missing or capture_failed or duplicate_captures or first_trade.get("all_cohort_first_trades_verified") is not True:
        blockers.append("official_capture_or_lifecycle_evidence_incomplete")

    coverage = (len(observed) / len(expected) * 100.0) if expected else None
    return {
        "status": "QUALITY_REVIEW_READY" if not blockers else "BLOCKED",
        "cohort_count": len(symbols), "identity_covered_symbols": len(valid_identity),
        "identity_errors": identity_errors,
        "verified_open_session_count": len(open_days), "expected_session_errors": session_errors,
        "expected_symbol_sessions": len(expected),
        "observed_panel_symbol_sessions": len(observed),
        "coverage_pct": round(coverage, 4) if coverage is not None else None,
        "missing_symbol_sessions": missing, "unexpected_panel_symbol_sessions": unexpected,
        "duplicate_panel_rows": duplicate_panel_rows, "panel_row_errors": row_errors,
        "source_conflicts": conflict_rows, "ingestion_errors": ingestion_errors,
        "insufficient_independent_source_coverage": insufficient,
        "missing_capture_keys": capture_missing, "failed_capture_keys": capture_failed,
        "duplicate_capture_ids": duplicate_captures,
        "first_trade_verification": {"verified_count": first_trade.get("verified_count"), "cohort_count": first_trade.get("cohort_count"), "unresolved_count": first_trade.get("unresolved_count"), "complete": first_trade.get("all_cohort_first_trades_verified") is True},
        "corporate_action_status": corporate_action_status.get("status"),
        "corporate_action_exceptions": corporate_exceptions,
        "panel_manifest_sha256": manifest_sha,
        "blocking_reasons": blockers,
        "backtest_admission_allowed": False, "canonical_promotion_allowed": False, "production_enabled": False,
        "limitations": [
            "Dashboard reflects only operator-supplied reports and the bounded cohort; it does not fetch or authenticate sources.",
            "Coverage denominator includes only supplied evidence-backed open sessions and supplied effective-dated identities.",
            "A clean dashboard is not proof of market-wide completeness and never grants replay admission.",
        ],
    }

"""Auditable coverage and exception dashboard for the bounded historical pilot."""
from __future__ import annotations
from datetime import date
from typing import Iterable, Mapping


def build_historical_pilot_quality_dashboard(
    *, cohort_symbols: Iterable[str], security_master: Iterable[Mapping[str, object]],
    expected_sessions: Iterable[Mapping[str, object]], panel_report: Mapping[str, object],
    reconciliation_report: Mapping[str, object], replay_preflight: Mapping[str, object],
    corporate_action_status: Mapping[str, object],
) -> dict:
    """Summarize supplied evidence without upgrading readiness or inventing missing rows."""
    symbols, master, sessions = list(cohort_symbols), list(security_master), list(expected_sessions)
    rows = list(panel_report.get("panel_rows", []))
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("cohort_symbols must be nonempty and unique")
    identity = {str(x.get("symbol")): x for x in master if str(x.get("symbol")) in symbols}
    open_days = set()
    for item in sessions:
        try:
            day = date.fromisoformat(str(item.get("session_date", "")))
        except ValueError:
            continue
        if item.get("status") == "confirmed_open" and item.get("evidence_id"):
            open_days.add(day.isoformat())
    expected = set()
    for symbol in symbols:
        item = identity.get(symbol)
        if not item:
            continue
        try:
            start = date.fromisoformat(str(item.get("effective_from", "")))
            end = date.fromisoformat(str(item["effective_to"])) if item.get("effective_to") else None
        except ValueError:
            continue
        for day_text in open_days:
            day = date.fromisoformat(day_text)
            if day >= start and (end is None or day <= end):
                expected.add((symbol, day_text))
    observed = set()
    for row in rows:
        try:
            key = (str(row["symbol"]), date.fromisoformat(str(row["session_date"])).isoformat())
        except (KeyError, ValueError, TypeError):
            continue
        observed.add(key)
    missing = [{"symbol": s, "session_date": d} for s, d in sorted(expected - observed)]
    unexpected = [{"symbol": s, "session_date": d} for s, d in sorted(observed - expected)]
    conflict_rows = list(panel_report.get("conflicts", []))
    ingestion_errors = list(panel_report.get("ingestion_errors", []))
    insufficient = list(panel_report.get("insufficient_source_coverage", []))
    capture_missing = list(reconciliation_report.get("missing_capture_keys", []))
    capture_failed = list(reconciliation_report.get("failed_capture_keys", []))
    duplicate_captures = list(reconciliation_report.get("duplicate_capture_ids", []))
    first_trade = reconciliation_report.get("first_trade_report", {})
    corporate_exceptions = list(corporate_action_status.get("withheld_events", [])) + list(corporate_action_status.get("rejected_events", []))
    coverage = (len(observed) / len(expected) * 100.0) if expected else None
    blockers = []
    if panel_report.get("status") != "PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH": blockers.append("panel_not_assembled")
    if reconciliation_report.get("status") != "SOURCE_EVIDENCE_RECONCILED": blockers.append("source_reconciliation_incomplete")
    if replay_preflight.get("status") != "BOUNDED_PILOT_REPLAY_PREFLIGHT_READY": blockers.append("replay_preflight_blocked")
    if corporate_action_status.get("status") != "validated_for_research" or corporate_exceptions: blockers.append("corporate_action_evidence_incomplete")
    if missing or unexpected or conflict_rows or ingestion_errors or insufficient: blockers.append("panel_coverage_or_integrity_exceptions")
    if capture_missing or capture_failed or duplicate_captures or first_trade.get("all_cohort_first_trades_verified") is not True: blockers.append("official_capture_or_lifecycle_evidence_incomplete")
    return {
        "status": "QUALITY_REVIEW_READY" if not blockers else "BLOCKED",
        "cohort_count": len(symbols), "identity_covered_symbols": len(identity),
        "verified_open_session_count": len(open_days), "expected_symbol_sessions": len(expected),
        "observed_panel_symbol_sessions": len(observed), "coverage_pct": round(coverage, 4) if coverage is not None else None,
        "missing_symbol_sessions": missing, "unexpected_panel_symbol_sessions": unexpected,
        "source_conflicts": conflict_rows, "ingestion_errors": ingestion_errors,
        "insufficient_independent_source_coverage": insufficient,
        "missing_capture_keys": capture_missing, "failed_capture_keys": capture_failed,
        "duplicate_capture_ids": duplicate_captures,
        "first_trade_verification": {"verified_count": first_trade.get("verified_count"), "cohort_count": first_trade.get("cohort_count"), "unresolved_count": first_trade.get("unresolved_count"), "complete": first_trade.get("all_cohort_first_trades_verified") is True},
        "corporate_action_status": corporate_action_status.get("status"),
        "corporate_action_exceptions": corporate_exceptions,
        "panel_manifest_sha256": replay_preflight.get("dataset_manifest", {}).get("sha256"),
        "blocking_reasons": blockers,
        "backtest_admission_allowed": False, "canonical_promotion_allowed": False, "production_enabled": False,
        "limitations": [
            "Dashboard reflects only operator-supplied reports and the bounded cohort; it does not fetch or authenticate sources.",
            "Coverage denominator includes only supplied evidence-backed open sessions and supplied effective-dated identities.",
            "A clean dashboard is not proof of market-wide completeness and never grants replay admission.",
        ],
    }

"""Fail-closed per-security historical pilot panel admission gates."""
from __future__ import annotations

import re
from datetime import date
from typing import Mapping

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HORIZON_MINIMUMS = {"t_plus_2": 5, "swing": 20, "positional": 60, "investment": 200}


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.lower()))


def audit_historical_pilot_panel_admission(
    *,
    expected_symbols: set[str],
    first_trade_report: Mapping,
    identity_by_symbol: Mapping[str, Mapping],
    calendar_by_symbol: Mapping[str, Mapping],
    ohlcv_by_symbol: Mapping[str, Mapping],
    corporate_actions_by_symbol: Mapping[str, Mapping],
    minimum_panel_sessions: int = 20,
) -> dict:
    """Return explicit per-symbol gates; absent evidence is blocked, never neutral."""
    if minimum_panel_sessions < 1:
        raise ValueError("minimum_panel_sessions must be positive")
    errors: list[str] = []
    if first_trade_report.get("status") != "validated_with_unresolved_first_trade_evidence":
        errors.append("first_trade_report_status_not_validated")
    if first_trade_report.get("errors"):
        errors.append("first_trade_report_contains_validation_errors")

    raw_floor_rows = first_trade_report.get("rows", [])
    floor_rows = {
        row.get("symbol"): row
        for row in raw_floor_rows
        if row.get("symbol")
    }
    if len(floor_rows) != len(raw_floor_rows):
        errors.append("first_trade_report_contains_duplicate_or_blank_symbols")

    results = []
    admitted = []
    for symbol in sorted(expected_symbols):
        blockers = []
        floor = floor_rows.get(symbol)
        if not floor or floor.get("official_floorsheet_status") != "verified_contract_match":
            blockers.append("official_first_trade_contract_not_verified")
        elif not floor.get("security_id") or not floor.get("reported_first_trade_date"):
            blockers.append("first_trade_contract_missing_security_identity_or_date")

        identity = identity_by_symbol.get(symbol)
        if not identity or identity.get("status") != "verified":
            blockers.append("effective_dated_security_identity_not_verified")
        else:
            if not identity.get("security_id") or not floor or identity.get("security_id") != floor.get("security_id"):
                blockers.append("effective_dated_security_identity_mismatch")
            if not identity.get("source_id") or not identity.get("evidence_id"):
                blockers.append("security_identity_provenance_missing")
            try:
                valid_from = date.fromisoformat(str(identity.get("valid_from")))
                valid_to_value = identity.get("valid_to")
                valid_to = date.fromisoformat(str(valid_to_value)) if valid_to_value else None
                trade_date = date.fromisoformat(str(floor.get("reported_first_trade_date"))) if floor else None
                if valid_to and valid_to < valid_from:
                    blockers.append("security_identity_validity_interval_invalid")
                if trade_date and (trade_date < valid_from or (valid_to and trade_date > valid_to)):
                    blockers.append("first_trade_outside_security_identity_validity")
            except (TypeError, ValueError):
                blockers.append("security_identity_effective_dates_invalid")

        calendar = calendar_by_symbol.get(symbol)
        if not calendar or calendar.get("status") != "verified_complete":
            blockers.append("exchange_session_calendar_not_verified_complete")
        else:
            if not calendar.get("source_id") or not _valid_digest(calendar.get("raw_sha256")):
                blockers.append("calendar_source_provenance_missing")
            try:
                expected = int(calendar.get("expected_sessions"))
                observed = int(calendar.get("observed_sessions"))
                missing = int(calendar.get("missing_sessions"))
                if expected < 1 or observed < 0 or missing != 0 or observed != expected:
                    blockers.append("calendar_session_coverage_incomplete")
                verified_open_dates = set(calendar.get("verified_open_dates", []))
                if floor and floor.get("reported_first_trade_date") not in verified_open_dates:
                    blockers.append("first_trade_date_not_verified_open_session")
            except (TypeError, ValueError):
                blockers.append("calendar_session_counts_invalid")

        ohlcv = ohlcv_by_symbol.get(symbol)
        if not ohlcv or ohlcv.get("status") != "verified_clean":
            blockers.append("ohlcv_quality_not_verified_clean")
        else:
            if not ohlcv.get("source_id"):
                blockers.append("ohlcv_source_provenance_missing")
            try:
                sessions = int(ohlcv.get("session_count"))
                anomalies = int(ohlcv.get("anomaly_count"))
                if sessions < minimum_panel_sessions:
                    blockers.append("insufficient_panel_session_history")
                if anomalies != 0:
                    blockers.append("ohlcv_anomalies_unresolved")
            except (TypeError, ValueError):
                blockers.append("ohlcv_quality_counts_invalid")
            if not _valid_digest(ohlcv.get("raw_sha256")):
                blockers.append("ohlcv_raw_sha256_missing_or_invalid")

        actions = corporate_actions_by_symbol.get(symbol)
        if not actions or actions.get("status") not in {"reconciled", "verified_no_actions"}:
            blockers.append("corporate_action_history_not_reconciled")
        else:
            try:
                source_ids = set(actions.get("source_ids", []))
                evidence_hashes = actions.get("evidence_sha256s", [])
                unresolved = int(actions.get("unresolved_event_count"))
                if len(source_ids) < 2 or len(evidence_hashes) < 2 or not all(_valid_digest(x) for x in evidence_hashes) or unresolved != 0:
                    blockers.append("corporate_action_independent_evidence_or_resolution_incomplete")
            except (TypeError, ValueError):
                blockers.append("corporate_action_evidence_counts_invalid")

        horizon_eligibility = {}
        session_count = 0
        if ohlcv:
            try:
                session_count = int(ohlcv.get("session_count", 0))
            except (TypeError, ValueError):
                session_count = 0
        for horizon, minimum in HORIZON_MINIMUMS.items():
            horizon_eligibility[horizon] = not blockers and session_count >= minimum

        if not blockers:
            admitted.append(symbol)
        results.append({
            "symbol": symbol,
            "status": "admitted_for_research_panel" if not blockers else "blocked",
            "blockers": blockers,
            "session_count": session_count,
            "horizon_eligibility": horizon_eligibility,
        })

    return {
        "status": "ready_for_research_panel" if len(admitted) == len(expected_symbols) and not errors else "blocked",
        "expected_symbol_count": len(expected_symbols),
        "admitted_symbol_count": len(admitted),
        "admitted_symbols": admitted,
        "blocked_symbol_count": len(results) - len(admitted),
        "errors": errors,
        "symbols": results,
        "canonical_promotion_allowed": False,
        "training_allowed": False,
        "production_enabled": False,
        "horizon_minimum_sessions": dict(HORIZON_MINIMUMS),
        "limitations": [
            "Admission is research-panel eligibility only, not strategy BUY eligibility.",
            "Horizon minimums are warm-up floors, not proof of statistical sufficiency.",
            "All evidence objects must be generated from point-in-time, source-retained records.",
            "Missing evidence is a blocker and is never imputed as neutral or clean.",
        ],
    }

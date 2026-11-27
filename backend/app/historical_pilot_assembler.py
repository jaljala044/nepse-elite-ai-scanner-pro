"""Assemble a deterministic pilot OHLCV panel from validated capture ingestions."""
from __future__ import annotations
from datetime import date, datetime
from typing import Iterable, Mapping

from app.historical_pilot_panel import build_lifecycle_panel_readiness

_FIELDS = ("open", "high", "low", "close", "volume")


def assemble_lifecycle_pilot_panel(
    *,
    cohort_symbols: Iterable[str],
    security_master: Iterable[Mapping[str, object]],
    expected_sessions: Iterable[Mapping[str, object]],
    ingestion_reports: Iterable[Mapping[str, object]],
    corporate_action_status: Mapping[str, object],
    decision_cutoff: str,
    minimum_independent_sources: int = 1,
) -> dict:
    """Build panel rows only where source values agree; quarantine conflicts."""
    symbols = list(cohort_symbols)
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("cohort_symbols must be nonempty and unique")
    if not isinstance(minimum_independent_sources, int) or minimum_independent_sources < 1:
        raise ValueError("minimum_independent_sources must be a positive integer")
    master = list(security_master)
    sessions = list(expected_sessions)
    reports = list(ingestion_reports)
    errors, grouped = [], {}
    for idx, report in enumerate(reports):
        if report.get("status") != "INGESTED" or report.get("all_rows_accepted") is not True:
            errors.append({"ingestion_index": idx, "reason": "ingestion_report_not_fully_validated"})
            continue
        for row in report.get("rows", []):
            symbol = str(row.get("symbol", ""))
            try:
                day = date.fromisoformat(str(row.get("session_date", "")))
                values = tuple(row.get(field) for field in _FIELDS)
            except (TypeError, ValueError):
                errors.append({"symbol": symbol or None, "reason": "invalid_ingested_row"})
                continue
            if symbol not in symbols:
                errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "symbol_outside_pilot_cohort"})
                continue
            if not row.get("source_id") or not row.get("publisher_id") or not row.get("raw_sha256") or not row.get("available_at"):
                errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "missing_row_provenance"})
                continue
            grouped.setdefault((symbol, day), []).append(row)
    identity_by_symbol = {str(x.get("symbol")): x for x in master if str(x.get("symbol")) in symbols}
    assembled, conflicts, insufficient = [], [], []
    for key in sorted(grouped, key=lambda x: (x[0], x[1])):
        symbol, day = key
        rows = grouped[key]
        distinct_values = {tuple(r.get(f) for f in _FIELDS) for r in rows}
        if len(distinct_values) != 1:
            conflicts.append({"symbol": symbol, "session_date": day.isoformat(), "source_ids": sorted({str(r.get("source_id")) for r in rows}), "reason": "cross_source_ohlcv_conflict"})
            continue
        source_ids = sorted({str(r["source_id"]) for r in rows})
        publishers = sorted({str(r["publisher_id"]) for r in rows})
        if len(publishers) < minimum_independent_sources:
            insufficient.append({"symbol": symbol, "session_date": day.isoformat(), "publisher_ids": publishers, "required_independent_publishers": minimum_independent_sources})
            continue
        identity = identity_by_symbol.get(symbol)
        if not identity:
            errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "permanent_security_identity_missing"})
            continue
        try:
            start = date.fromisoformat(str(identity.get("effective_from", "")))
            end = date.fromisoformat(str(identity["effective_to"])) if identity.get("effective_to") else None
        except ValueError:
            errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "invalid_security_lifecycle"})
            continue
        if day < start or (end and day > end):
            errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "bar_outside_security_lifecycle"})
            continue
        values = next(iter(distinct_values))
        first = sorted(rows, key=lambda r: (str(r["source_id"]), str(r["capture_id"]), int(r["page_number"]), int(r["source_row_number"])))[0]
        assembled.append({"symbol": symbol, "security_id": str(identity["security_id"]), "session_date": day.isoformat(), **dict(zip(_FIELDS, values)), "available_at": max((str(r["available_at"]) for r in rows), key=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))), "raw_sha256": first["raw_sha256"], "source_ids": source_ids, "publisher_ids": publishers, "capture_ids": sorted({str(r["capture_id"]) for r in rows}), "row_hashes": sorted({str(r["row_sha256"]) for r in rows})})
    # Use the strict existing validator for calendar, coverage, cutoff and corporate actions.
    readiness_bars = [{k: r[k] for k in ("symbol", "session_date", "open", "high", "low", "close", "volume", "available_at", "raw_sha256")} for r in assembled]
    readiness = build_lifecycle_panel_readiness(cohort_symbols=symbols, security_master=master, expected_sessions=sessions, bars=readiness_bars, corporate_action_status=corporate_action_status, decision_cutoff=decision_cutoff)
    ready = readiness.get("status") == "READY_FOR_BOUNDED_RESEARCH" and not errors and not conflicts and not insufficient
    return {"status": "PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH" if ready else "BLOCKED", "panel_rows": assembled, "panel_row_count": len(assembled), "conflicts": conflicts, "insufficient_source_coverage": insufficient, "ingestion_errors": errors, "readiness_report": readiness, "minimum_independent_sources": minimum_independent_sources, "backtest_admission_allowed": False, "canonical_promotion_allowed": False, "production_enabled": False, "limitations": ["This panel is assembled only from caller-supplied validated ingestion reports.", "Agreement between sources does not prove publisher independence or source completeness.", "No rows are synthesized for missing sessions; conflicts and gaps remain visible.", "A ready panel is bounded research only and requires separate human admission."]}

"""Dataset admission registry and readiness gate for NEPSE research history.

This module registers reports produced by the captured-byte intake adapter. It
never fetches data or treats a manifest assertion as publisher authentication.
"""
from __future__ import annotations
from datetime import datetime, timezone

REQUIRED_DATASETS = ("ohlcv", "session_calendar", "instrument_universe", "corporate_actions")
OPTIONAL_DATASETS = ("floorsheet", "broker_summary", "sector_membership", "sector_index", "fundamentals")
ALL_DATASETS = REQUIRED_DATASETS + OPTIONAL_DATASETS

def _time(value):
    if not isinstance(value, str): return None
    try: result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    if result.tzinfo is None or result.utcoffset() is None: return None
    return result.astimezone(timezone.utc)

def build_dataset_registry(*, intake_reports, decision_cutoff, expected_start_date=None, expected_end_date=None):
    """Build a fail-closed registry from validated intake reports.

    Each report must be the output of ingest_captured_csv (or an equivalent
    reviewed intake process) and include a complete source envelope.
    """
    cutoff = _time(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(intake_reports, dict): raise ValueError("intake_reports_required")
    errors, registry = [], {}
    unknown = sorted(set(intake_reports) - set(ALL_DATASETS))
    if unknown: errors.extend("unsupported_dataset:" + k for k in unknown)
    for kind in ALL_DATASETS:
        report = intake_reports.get(kind)
        error_count_before_dataset = len(errors)
        if report is None:
            if kind in REQUIRED_DATASETS: errors.append("required_dataset_missing:" + kind)
            continue
        if not isinstance(report, dict) or report.get("dataset_kind") != kind:
            errors.append("dataset_report_invalid:" + kind); continue
        env = report.get("source_envelope")
        validation = report.get("validation")
        if report.get("status") != "validated_for_research" or not isinstance(validation, dict) or validation.get("research_review_allowed") is not True:
            errors.append("dataset_not_validated:" + kind)
        if not isinstance(env, dict):
            errors.append("source_envelope_missing:" + kind); continue
        available = _time(env.get("available_at"))
        if available is None or available > cutoff: errors.append("dataset_not_point_in_time:" + kind)
        for field in ("source_id", "publisher", "evidence_id", "raw_sha256", "registry_review_id"):
            if not isinstance(env.get(field), str) or not env[field].strip():
                errors.append("provenance_missing:" + kind + ":" + field)
        digest = str(env.get("raw_sha256", "")).lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            errors.append("raw_hash_invalid:" + kind)
        if env.get("rights_status") != "approved": errors.append("rights_not_approved:" + kind)
        if env.get("source_validation_status") != "verified": errors.append("source_not_verified:" + kind)
        if env.get("finality_status") != "final": errors.append("source_not_final:" + kind)
        rows = validation.get("accepted_rows") if isinstance(validation, dict) else None
        if not isinstance(rows, list) or not rows: errors.append("accepted_rows_missing:" + kind)
        registry[kind] = {
            "dataset_kind": kind, "source_id": env.get("source_id"),
            "publisher": env.get("publisher"), "evidence_id": env.get("evidence_id"),
            "raw_sha256": digest, "available_at": available.isoformat() if available else None,
            "row_count": len(rows) if isinstance(rows, list) else 0,
            "captured_at": report.get("captured_at"),
            "status": "admitted" if len(errors) == error_count_before_dataset else "withheld",
        }
    admitted_required = all(k in registry and registry[k]["status"] == "admitted" for k in REQUIRED_DATASETS)
    start, end = expected_start_date, expected_end_date
    if (start is None) != (end is None): raise ValueError("expected_date_range_requires_both_bounds")
    if start is not None:
        try:
            if datetime.fromisoformat(start).date() > datetime.fromisoformat(end).date(): raise ValueError("expected_date_range_invalid")
        except (TypeError, ValueError): raise ValueError("expected_date_range_invalid") from None
    missing_optional = [k for k in OPTIONAL_DATASETS if k not in registry]
    quality = "LOW" if errors or not admitted_required else ("MEDIUM" if missing_optional else "HIGH")
    return {
        "schema_version": "nepse-dataset-registry-1.0.0",
        "status": "ready_for_panel_assembly" if admitted_required and not errors else "blocked",
        "decision_cutoff": cutoff.isoformat(), "expected_start_date": start, "expected_end_date": end,
        "datasets": registry, "required_dataset_coverage_pct": str(
            sum(1 for k in REQUIRED_DATASETS if k in registry and registry[k]["status"] == "admitted") / len(REQUIRED_DATASETS) * 100),
        "optional_datasets_missing": missing_optional, "errors": errors, "data_quality": quality,
        "live_data_acquired": False, "publisher_authenticity_verified": False,
        "performance_claimed": False, "production_enabled": False,
        "limitations": [
            "Registry validates intake report structure and declared provenance; it does not independently authenticate publishers or licences.",
            "Optional floorsheet, broker, sector and fundamental datasets are not silently imputed when absent.",
            "A ready registry is only permission to attempt panel assembly, not proof of a complete or tradable historical sample."
        ]
    }

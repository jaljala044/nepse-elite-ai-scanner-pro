"""Fail-closed dataset admission and temporal leakage checks for six scanners."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Mapping

STRATEGIES = (
    "trend_momentum", "idpat_smart_money", "broker_footprint",
    "smc_ict_liquidity", "hybrid_consensus", "fundamental_investment",
)
HORIZONS = ("t_plus_2", "swing", "positional", "investment")


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result.astimezone(timezone.utc)


def admit_six_scanner_dataset(
    *, panel_qualification: Mapping, dataset_manifest: Mapping,
    records: list[Mapping], decision_time: str,
    expected_dataset_fingerprint: str,
    train_end: str, validation_start: str, validation_end: str,
    test_start: str, test_end: str,
    strategy_ids: tuple[str, ...] = STRATEGIES,
    horizons: tuple[str, ...] = HORIZONS,
) -> dict:
    """Validate one shared point-in-time dataset before any of the 24 replays.

    This is an admission report only; it never starts replay or authorizes
    canonical promotion/production. Each row must carry available_at and may
    optionally carry feature_available_at/label_available_at timestamps.
    """
    issues = []
    cutoff = _utc(decision_time, "decision_time")
    train = _utc(train_end, "train_end")
    val_start = _utc(validation_start, "validation_start")
    val_end = _utc(validation_end, "validation_end")
    test_begin = _utc(test_start, "test_start")
    test_finish = _utc(test_end, "test_end")
    if not train < val_start <= val_end < test_begin <= test_finish:
        issues.append({"severity": "BLOCKER", "reason": "train_validation_test_windows_not_strictly_chronological"})
    if test_begin <= cutoff:
        issues.append({"severity": "BLOCKER", "reason": "test_window_not_untouched_after_decision_cutoff"})

    fingerprint = str(dataset_manifest.get("dataset_fingerprint", ""))
    if not fingerprint or fingerprint != expected_dataset_fingerprint:
        issues.append({"severity": "BLOCKER", "reason": "dataset_fingerprint_missing_or_mismatched"})
    manifest_cutoff = dataset_manifest.get("decision_time")
    try:
        if _utc(str(manifest_cutoff), "manifest.decision_time") != cutoff:
            issues.append({"severity": "BLOCKER", "reason": "manifest_decision_time_mismatch"})
    except ValueError:
        issues.append({"severity": "BLOCKER", "reason": "manifest_decision_time_missing_or_invalid"})
    if panel_qualification.get("status") != "PANEL_EVIDENCE_QUALIFIED_FOR_HUMAN_REVIEW":
        issues.append({"severity": "BLOCKER", "reason": "historical_panel_not_qualified_for_human_review"})
    if panel_qualification.get("backtest_admission_allowed") is not False:
        issues.append({"severity": "BLOCKER", "reason": "panel_gate_must_not_pre_authorize_backtest_admission"})
    if dataset_manifest.get("corporate_action_review_status") != "verified":
        issues.append({"severity": "BLOCKER", "reason": "corporate_action_review_not_verified"})
    if dataset_manifest.get("input_lineage_status") != "complete":
        issues.append({"severity": "BLOCKER", "reason": "input_lineage_incomplete"})
    if panel_qualification.get("dataset_fingerprint") != fingerprint:
        issues.append({"severity": "BLOCKER", "reason": "panel_dataset_fingerprint_mismatch"})

    future, missing, duplicate_ids, invalid = [], [], [], []
    seen_ids = set()
    for index, row in enumerate(records):
        if not isinstance(row, Mapping):
            invalid.append(index)
            continue
        record_id = row.get("record_id")
        if record_id:
            if record_id in seen_ids:
                duplicate_ids.append(str(record_id))
            seen_ids.add(record_id)
        try:
            available = _utc(str(row.get("available_at", "")), f"records[{index}].available_at")
        except ValueError:
            missing.append(index)
            continue
        if available > cutoff:
            future.append({"index": index, "available_at": available.isoformat()})
        for field in ("feature_available_at", "label_available_at"):
            if row.get(field) is not None:
                try:
                    timestamp = _utc(str(row[field]), f"records[{index}].{field}")
                    if timestamp > cutoff:
                        future.append({"index": index, "field": field, "timestamp": timestamp.isoformat()})
                except ValueError:
                    invalid.append(index)
    if missing:
        issues.append({"severity": "BLOCKER", "reason": "records_missing_available_at", "indexes": missing})
    if future:
        issues.append({"severity": "BLOCKER", "reason": "future_information_leakage", "records": future})
    if duplicate_ids:
        issues.append({"severity": "BLOCKER", "reason": "duplicate_record_ids", "record_ids": sorted(set(duplicate_ids))})
    if invalid:
        issues.append({"severity": "BLOCKER", "reason": "invalid_record_or_timestamp", "indexes": sorted(set(invalid))})

    expected = {(strategy, horizon) for strategy in strategy_ids for horizon in horizons}
    if (set(strategy_ids) != set(STRATEGIES) or set(horizons) != set(HORIZONS)
            or len(strategy_ids) != len(set(strategy_ids))
            or len(horizons) != len(set(horizons))):
        issues.append({"severity": "BLOCKER", "reason": "six_strategy_four_horizon_matrix_must_be_complete"})
    matrix = [{"strategy_id": strategy, "horizon": horizon,
               "status": "ADMITTED_FOR_HUMAN_REVIEW" if not issues else "BLOCKED"}
              for strategy, horizon in sorted(expected)]
    blockers = sum(item["severity"] == "BLOCKER" for item in issues)
    payload = {
        "schema_version": 1, "dataset_fingerprint": fingerprint or None,
        "decision_time": cutoff.isoformat().replace("+00:00", "Z"),
        "strategy_count": len(strategy_ids), "horizon_count": len(horizons),
        "strategy_horizon_count": len(matrix), "matrix": matrix,
        "record_count": len(records), "issue_count": len(issues),
        "blocker_count": blockers, "issues": issues,
        "status": "ADMITTED_FOR_HUMAN_REVIEW" if not issues else "BLOCKED",
        "replay_started": False, "probabilities_calibrated": False,
        "canonical_promotion_allowed": False, "production_enabled": False,
        "limitations": [
            "Admission is a deterministic preflight, not evidence of strategy profitability.",
            "The untouched test interval must be evaluated by the replay runner using per-observation cutoffs.",
            "Human review and a separate replay authorization remain mandatory.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["admission_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload

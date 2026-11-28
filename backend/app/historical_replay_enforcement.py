"""Enforce dataset admission and per-observation point-in-time leakage before replay."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping

from app.historical_dataset_admission import admit_six_scanner_dataset
from app.historical_pilot_replay_admission import (
    STRATEGIES, HORIZONS, evaluate_six_scanner_replay_admission,
)
from app.historical_pilot_replay_runner import run_admitted_six_scanner_replay


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_missing_or_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_missing_or_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def audit_point_in_time_replay_observations(
    observations: Iterable[Mapping[str, object]],
) -> dict:
    """Audit each historical decision independently; labels remain outcome-only."""
    rows = list(observations)
    issues = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            issues.append({"index": index, "reason": "observation_not_mapping"})
            continue
        observation_id = str(row.get("observation_id", "")).strip()
        if not observation_id:
            issues.append({"index": index, "reason": "observation_id_missing"})
        elif observation_id in seen:
            issues.append({"index": index, "reason": "duplicate_observation_id", "observation_id": observation_id})
        seen.add(observation_id)
        try:
            decision_at = _utc(row.get("decision_at"), "decision_at")
        except ValueError as exc:
            issues.append({"index": index, "reason": str(exc)})
            continue
        features = row.get("features")
        if not isinstance(features, list) or not features:
            issues.append({"index": index, "reason": "point_in_time_features_missing"})
            continue
        feature_ids = set()
        for feature_index, feature in enumerate(features):
            if not isinstance(feature, Mapping):
                issues.append({"index": index, "feature_index": feature_index, "reason": "feature_not_mapping"})
                continue
            feature_id = str(feature.get("feature_id", "")).strip()
            if not feature_id or feature_id in feature_ids:
                issues.append({"index": index, "feature_index": feature_index, "reason": "feature_id_missing_or_duplicate"})
            feature_ids.add(feature_id)
            if any(key in feature for key in ("label", "target", "future_return", "outcome")):
                issues.append({"index": index, "feature_index": feature_index, "reason": "outcome_field_embedded_in_features"})
            try:
                feature_available = _utc(feature.get("available_at"), "feature_available_at")
                source_available = _utc(feature.get("source_available_at"), "source_available_at")
                if feature_available > decision_at:
                    issues.append({"index": index, "feature_index": feature_index, "reason": "feature_available_after_decision"})
                if source_available > decision_at:
                    issues.append({"index": index, "feature_index": feature_index, "reason": "source_available_after_decision"})
            except ValueError as exc:
                issues.append({"index": index, "feature_index": feature_index, "reason": str(exc)})
        if "label" in row or "target" in row or "future_return" in row:
            try:
                outcome_end = _utc(row.get("outcome_end_at"), "outcome_end_at")
                label_available = _utc(row.get("label_available_at"), "label_available_at")
                if outcome_end <= decision_at:
                    issues.append({"index": index, "reason": "outcome_window_not_after_decision"})
                if label_available <= decision_at or label_available < outcome_end:
                    issues.append({"index": index, "reason": "label_available_before_outcome_complete"})
            except ValueError as exc:
                issues.append({"index": index, "reason": str(exc)})
    canonical = json.dumps({"observation_count": len(rows), "issues": issues}, sort_keys=True, separators=(",", ":"))
    return {
        "status": "POINT_IN_TIME_CLEAN" if not issues else "LEAKAGE_BLOCKED",
        "observation_count": len(rows), "issue_count": len(issues), "issues": issues,
        "audit_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "labels_used_as_features": False,
        "limitations": [
            "The audit validates supplied timestamps and field placement; it cannot independently prove publisher timestamps or feature calculation correctness.",
            "All raw feature inputs must be represented as separate feature records with source availability timestamps.",
        ],
    }


def enforce_and_run_six_scanner_replay(
    *,
    dataset_admission_kwargs: Mapping[str, object],
    quality_dashboard: Mapping[str, object],
    replay_preflight: Mapping[str, object],
    strategy_ids: list[str], horizons: list[str],
    dataset_manifest_sha256: str, partition: str,
    cost_model: Mapping[str, object], execution_model: Mapping[str, object],
    human_review: Mapping[str, object],
    observations: Iterable[Mapping[str, object]],
    panel_rows: Iterable[Mapping[str, object]],
    run_one: Callable[..., Mapping[str, object]],
) -> dict:
    """One enforced path: dataset gate -> per-row leakage -> human approval -> 24 runs."""
    dataset_admission = admit_six_scanner_dataset(**dict(dataset_admission_kwargs))
    leakage = audit_point_in_time_replay_observations(observations)
    errors = []
    if dataset_admission.get("status") != "ADMITTED_FOR_HUMAN_REVIEW":
        errors.append("point_in_time_dataset_admission_blocked")
    if dataset_admission.get("dataset_fingerprint") != dataset_manifest_sha256:
        errors.append("dataset_fingerprint_does_not_match_replay_manifest")
    if leakage.get("status") != "POINT_IN_TIME_CLEAN":
        errors.append("per_observation_leakage_audit_blocked")
    if partition != "untouched_out_of_sample":
        errors.append("partition_must_be_untouched_out_of_sample")
    if errors:
        return {
            "status": "BLOCKED", "dataset_admission": dataset_admission,
            "leakage_audit": leakage, "replay_admission": None,
            "replay_result": {"status": "BLOCKED", "runs": [], "historical_replay_executed": False},
            "blocking_reasons": errors, "historical_replay_executed": False,
            "canonical_promotion_allowed": False, "production_enabled": False,
        }
    replay_admission = evaluate_six_scanner_replay_admission(
        quality_dashboard=quality_dashboard, replay_preflight=replay_preflight,
        strategy_ids=strategy_ids, horizons=horizons,
        dataset_manifest_sha256=dataset_manifest_sha256, partition=partition,
        cost_model=cost_model, execution_model=execution_model,
        human_review=human_review,
    )
    if replay_admission.get("admitted") is not True:
        return {
            "status": "BLOCKED", "dataset_admission": dataset_admission,
            "leakage_audit": leakage, "replay_admission": replay_admission,
            "replay_result": {"status": "BLOCKED", "runs": [], "historical_replay_executed": False},
            "blocking_reasons": list(replay_admission.get("blocking_reasons", [])),
            "historical_replay_executed": False, "canonical_promotion_allowed": False,
            "production_enabled": False,
        }
    replay_result = run_admitted_six_scanner_replay(
        admission_report=replay_admission,
        dataset_manifest_sha256=dataset_manifest_sha256,
        panel_rows=panel_rows, run_one=run_one,
    )
    complete = replay_result.get("status") == "RESEARCH_REPLAY_COMPLETED"
    return {
        "status": "RESEARCH_REPLAY_COMPLETED" if complete else "RESEARCH_REPLAY_INCOMPLETE",
        "dataset_admission": dataset_admission, "leakage_audit": leakage,
        "replay_admission": replay_admission, "replay_result": replay_result,
        "blocking_reasons": [], "historical_replay_executed": replay_result.get("historical_replay_executed") is True,
        "run_count": replay_result.get("run_count", 0),
        "expected_run_count": len(STRATEGIES) * len(HORIZONS),
        "common_dataset_fingerprint": dataset_manifest_sha256,
        "performance_metrics_interpreted": False, "probabilities_calibrated": False,
        "canonical_promotion_allowed": False, "production_enabled": False,
        "limitations": [
            "A completed run is not evidence of profitability; metrics require independent OOS review.",
            "The injected runner must enforce realistic NEPSE costs, fills, liquidity, settlement and price-limit rules.",
            "Timestamp checks cannot prove source authenticity or correct feature engineering.",
        ],
    }

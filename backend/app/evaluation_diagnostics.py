"""Dataset coverage, missingness and leakage diagnostics for forecast evaluation."""
from __future__ import annotations

from datetime import datetime, timezone
from math import log

from app.scenario_validation import walk_forward_splits


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _metrics(rows: list[dict], baseline: float) -> dict:
    if not rows:
        return {"status": "insufficient_sample", "sample_count": 0}
    actual = [int(row["actual"]) for row in rows]
    probability = [float(row["probability"]) for row in rows]
    if any(y not in (0, 1) for y in actual) or any(not 0 <= p <= 1 for p in probability):
        raise ValueError("labels must be binary and probabilities in [0,1]")
    eps = 1e-15
    brier = sum((p-y)**2 for y, p in zip(actual, probability)) / len(rows)
    loss = -sum(y*log(max(p, eps)) + (1-y)*log(max(1-p, eps))
                for y, p in zip(actual, probability)) / len(rows)
    baseline_brier = sum((baseline-y)**2 for y in actual) / len(rows)
    return {"status": "evaluated", "sample_count": len(rows),
            "brier_score": brier, "log_loss": loss,
            "training_prevalence_baseline": baseline,
            "baseline_brier_score": baseline_brier,
            "brier_skill_vs_training_baseline": (1-brier/baseline_brier if baseline_brier else None)}


def build_evaluation_diagnostics(forecasts: list[dict], expected_decision_dates: list[str],
                                 min_train_dates: int, test_dates: int) -> dict:
    """Exclude missing/duplicate/leaked forecasts and use only matured labels in train folds.

    Required fields: forecast_id, observation_date, decision_time,
    max_input_available_at, label_available_at, actual, probability.
    """
    expected = sorted(set(expected_decision_dates))
    seen = {}
    duplicates = []
    for row in forecasts:
        key = row["observation_date"]
        seen.setdefault(key, []).append(row)
    for key, rows in seen.items():
        if len(rows) > 1:
            duplicates.append(key)
    missing_dates = sorted(set(expected) - set(seen))
    eligible = []
    leakage = []
    missing_labels = []
    for row in forecasts:
        reason = None
        if row.get("actual") is None or row.get("probability") is None or not row.get("label_available_at"):
            missing_labels.append(row["forecast_id"])
            continue
        decision = _utc(row["decision_time"])
        max_input = _utc(row["max_input_available_at"])
        label_available = _utc(row["label_available_at"])
        if max_input > decision:
            reason = "future_input_available_after_decision"
        elif label_available <= decision:
            reason = "label_known_at_or_before_decision"
        if reason:
            leakage.append({"forecast_id": row["forecast_id"], "reason": reason})
        else:
            eligible.append(row)
    # Duplicate dates are not scored: absent a defined multi-forecast aggregation
    # the report fails closed instead of selecting a convenient row.
    eligible = [row for row in eligible if row["observation_date"] not in duplicates]
    dates = sorted({row["observation_date"] for row in eligible})
    folds = walk_forward_splits(dates, min_train_dates, test_dates)
    fold_reports = []
    for number, fold in enumerate(folds, 1):
        test = [r for r in eligible if fold["test_start"] <= r["observation_date"] <= fold["test_end"]]
        if not test:
            continue
        test_start_time = min(_utc(r["decision_time"]) for r in test)
        train = [r for r in eligible if r["observation_date"] <= fold["train_end"]
                 and _utc(r["label_available_at"]) < test_start_time]
        if not train:
            fold_reports.append({"fold": number, **fold, "status": "insufficient_matured_training_labels",
                                 "train_rows": 0, "test_rows": len(test)})
            continue
        baseline = sum(int(r["actual"]) for r in train) / len(train)
        fold_reports.append({"fold": number, **fold, "train_rows": len(train),
                             "test_rows": len(test), **_metrics(test, baseline)})
    return {
        "status": "evaluated" if fold_reports else "insufficient_sample",
        "expected_decision_dates": len(expected),
        "received_forecasts": len(forecasts),
        "covered_dates": len(seen),
        "missing_decision_dates": missing_dates,
        "duplicate_decision_dates": duplicates,
        "missing_label_forecast_ids": sorted(missing_labels),
        "leakage_exceptions": sorted(leakage, key=lambda x: x["forecast_id"]),
        "eligible_forecast_count": len(eligible),
        "coverage_ratio": len(set(seen) & set(expected)) / len(expected) if expected else None,
        "fold_count": len(fold_reports), "folds": fold_reports,
        "scoring_policy": "unique_date_only; point-in-time inputs; matured training labels only; duplicate dates excluded",
    }

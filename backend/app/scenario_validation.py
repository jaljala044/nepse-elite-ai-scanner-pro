"""Small, dependency-free probabilistic evaluation metrics for scenario forecasts."""
from __future__ import annotations

from math import log


def validate_binary_forecasts(actual: list[int], probability: list[float]) -> dict:
    if len(actual) != len(probability):
        raise ValueError("actual and probability lengths differ")
    if not actual:
        return {"status": "insufficient_sample", "sample_count": 0}
    if any(y not in (0, 1) for y in actual):
        raise ValueError("actual labels must be 0 or 1")
    if any(not 0 <= p <= 1 for p in probability):
        raise ValueError("probabilities must be between 0 and 1")
    eps = 1e-15
    brier = sum((p-y)**2 for y,p in zip(actual, probability)) / len(actual)
    log_loss = -sum(y*log(max(p,eps)) + (1-y)*log(max(1-p,eps))
                    for y,p in zip(actual, probability)) / len(actual)
    prevalence = sum(actual) / len(actual)
    baseline_brier = sum((prevalence-y)**2 for y in actual) / len(actual)
    return {
        "status": "evaluated",
        "sample_count": len(actual),
        "event_prevalence": prevalence,
        "brier_score": brier,
        "log_loss": log_loss,
        "constant_prevalence_baseline_brier": baseline_brier,
        "brier_skill_vs_prevalence": (
            1 - brier / baseline_brier if baseline_brier > 0 else None
        ),
        "warning": "metrics are descriptive; use chronological holdout and calibration data not used for fitting",
    }


def walk_forward_splits(observation_dates: list[str], min_train: int, test_size: int, step: int | None = None) -> list[dict]:
    """Create expanding chronological folds from already sorted unique dates."""
    dates = sorted(set(observation_dates))
    if min_train < 1 or test_size < 1:
        raise ValueError("min_train and test_size must be positive")
    stride = step or test_size
    if stride < 1:
        raise ValueError("step must be positive")
    folds = []
    start = min_train
    while start + test_size <= len(dates):
        folds.append({
            "train_start": dates[0],
            "train_end": dates[start - 1],
            "test_start": dates[start],
            "test_end": dates[start + test_size - 1],
            "train_count": start,
            "test_count": test_size,
        })
        start += stride
    return folds

"""Reproducible chronological forecast evaluation with train-only prevalence baseline."""
from __future__ import annotations

from math import isfinite, log
from datetime import date
from app.scenario_validation import walk_forward_splits
from app.quarantine_guard import is_quarantined, runtime_quarantine_keys


def _scores(actual: list[int], probability: list[float], baseline_probability: float) -> dict:
    if not actual:
        return {"sample_count": 0, "status": "insufficient_sample"}
    eps = 1e-15
    brier = sum((p-y)**2 for y, p in zip(actual, probability)) / len(actual)
    loss = -sum(y*log(max(p, eps)) + (1-y)*log(max(1-p, eps))
                for y, p in zip(actual, probability)) / len(actual)
    baseline_brier = sum((baseline_probability-y)**2 for y in actual) / len(actual)
    return {"status": "evaluated", "sample_count": len(actual),
            "brier_score": brier, "log_loss": loss,
            "train_prevalence_baseline": baseline_probability,
            "baseline_brier_score": baseline_brier,
            "brier_skill_vs_train_baseline": (
                1-brier/baseline_brier if baseline_brier > 0 else None)}


def build_walk_forward_report(rows: list[dict], min_train_dates: int,
                              test_dates: int, step_dates: int | None = None, *, require_ledger: bool = False) -> dict:
    """Rows require one binary outcome and probability per dated forecast.

    Each fold's benchmark prevalence is calculated only from outcomes strictly
    before that fold's test start. No shuffled splits or test-derived baseline.
    """
    keys = runtime_quarantine_keys(required=require_ledger)
    normalized_rows = []
    for index, row in enumerate(rows):
        try:
            observation_date = date.fromisoformat(str(row["observation_date"])).isoformat()
            if is_quarantined(row):
                raise ValueError("quarantined forecast input")
            if keys is not None:
                symbol = row.get("symbol")
                sessions = row.get("constituent_sessions")
                if not isinstance(symbol, str) or not symbol.strip() or not isinstance(sessions, list) or not sessions:
                    raise ValueError("missing forecast symbol or constituent-session lineage")
                dates_used = [date.fromisoformat(day).isoformat() for day in sessions]
                if dates_used != sessions or len(set(dates_used)) != len(dates_used) or observation_date not in dates_used:
                    raise ValueError("invalid forecast constituent-session lineage")
                if any((symbol.strip().upper(), day) in keys for day in dates_used):
                    raise ValueError("quarantined forecast constituent session")
            actual_value = row["actual"]
            if isinstance(actual_value, bool) or actual_value not in (0, 1, "0", "1"):
                raise ValueError("actual must be exactly binary 0 or 1")
            probability = float(row["probability"])
            if not isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError("probability must be finite and between zero and one")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"invalid walk-forward row {index}: {exc}") from exc
        normalized_rows.append({**row, "observation_date": observation_date,
                                "actual": int(actual_value), "probability": probability})
    ordered = sorted(normalized_rows, key=lambda r: (r["observation_date"], r.get("forecast_id", "")))
    dates = sorted({r["observation_date"] for r in ordered})
    folds = walk_forward_splits(dates, min_train_dates, test_dates, step_dates)
    reports = []
    for index, fold in enumerate(folds, 1):
        train = [r for r in ordered if r["observation_date"] <= fold["train_end"]]
        test = [r for r in ordered if fold["test_start"] <= r["observation_date"] <= fold["test_end"]]
        if any(r["observation_date"] > fold["train_end"] for r in train):
            raise AssertionError("training window crossed into test period")
        if any(r["observation_date"] < fold["test_start"] for r in test):
            raise AssertionError("test window crossed before test period")
        if not train:
            continue
        labels = [r["actual"] for r in test]
        probabilities = [r["probability"] for r in test]
        prevalence = sum(int(r["actual"]) for r in train) / len(train)
        reports.append({"fold": index, **fold, "train_rows": len(train),
                        "test_rows": len(test), **_scores(labels, probabilities, prevalence)})
    return {"status": "evaluated" if reports else "insufficient_sample",
            "fold_count": len(reports), "folds": reports,
            "quarantine_ledger_checked": keys is not None,
            "approved_backtest_eligible": False, "production_promotion_allowed": False,
            "warning": "synthetic or unverified records do not establish predictive value; report source and point-in-time gates separately"}

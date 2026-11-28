"""Reporting bridge from verified sector rotation into market-health outputs.

The bridge preserves evidence status and descriptive labels. It never creates
broker-flow metrics, official sector-index returns, stock recommendations or
probabilities from constituent-price data.
"""
from __future__ import annotations

from math import isfinite

WINDOWS = ("1W", "1M", "3M", "6M")
CLASSIFICATIONS = {"Leading", "Improving", "Neutral", "Weakening", "Lagging"}


def _valid_number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label}_must_be_finite_number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label}_must_be_finite_number") from None
    if not isfinite(number):
        raise ValueError(f"{label}_must_be_finite_number")
    return number


def _validated(rotation: dict, decision_session: str) -> dict:
    if not isinstance(rotation, dict):
        raise ValueError("sector_rotation_must_be_object")
    if rotation.get("status") != "observed" or rotation.get("mode") != "descriptive_only":
        raise ValueError("sector_rotation_not_observed_descriptive_only")
    if rotation.get("as_of_session") != decision_session:
        raise ValueError("sector_rotation_as_of_session_mismatch")
    sectors = rotation.get("sectors")
    if not isinstance(sectors, dict) or not sectors:
        raise ValueError("sector_rotation_results_missing")
    expected = rotation.get("sector_count")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected != len(sectors):
        raise ValueError("sector_rotation_sector_count_mismatch")
    coverage = _valid_number(rotation.get("sector_coverage_pct"), "sector_coverage_pct")
    if not 0 <= coverage <= 100:
        raise ValueError("sector_coverage_pct_out_of_range")
    return sectors


def adapt_verified_sector_rotation(rotation: dict, *, decision_session: str) -> dict:
    """Translate sector median returns to the existing market-health adapter schema."""
    sectors = _validated(rotation, decision_session)
    adapted = {}
    for name, detail in sectors.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(detail, dict):
            raise ValueError("invalid_sector_rotation_detail")
        source_windows = detail.get("windows")
        windows = {}
        for label in WINDOWS:
            item = source_windows.get(label) if isinstance(source_windows, dict) else None
            if not isinstance(item, dict) or item.get("status") != "observed":
                windows[label] = {"status": "insufficient_evidence", "median_return_pct": None}
                continue
            windows[label] = {
                "status": "observed",
                "median_return_pct": _valid_number(
                    item.get("median_return_pct"), f"{name}_{label}_median_return_pct"
                ),
            }
        adapted[name] = {"windows": windows}
    return {
        "status": "observed",
        "as_of_session": decision_session,
        "method": "median_constituent_return_cross_sector_percentile",
        "sectors": adapted,
        "source_mode": "verified_sector_rotation_descriptive_only",
    }


def sector_rotation_report(rotation: dict, *, decision_session: str) -> dict:
    """Return an auditable ranked report; unsupported classifications stay withheld."""
    sectors = _validated(rotation, decision_session)
    rows = []
    for name, detail in sectors.items():
        if not isinstance(name, str) or not isinstance(detail, dict):
            raise ValueError("invalid_sector_rotation_detail")
        classification = detail.get("classification")
        score = detail.get("weighted_excess_return_pct")
        rank = detail.get("relative_strength_rank_pct")
        if detail.get("score_status") != "observed" or classification not in CLASSIFICATIONS:
            classification = "insufficient_evidence"
            score = None
            rank = None
        else:
            score = _valid_number(score, f"{name}_weighted_excess_return_pct")
            rank = _valid_number(rank, f"{name}_relative_strength_rank_pct")
            if not 0 <= rank <= 100:
                raise ValueError(f"{name}_relative_strength_rank_out_of_range")
        windows = detail.get("windows") if isinstance(detail.get("windows"), dict) else {}
        window_metrics = {}
        for label in WINDOWS:
            item = windows.get(label)
            if isinstance(item, dict) and item.get("status") == "observed":
                window_metrics[label] = {
                    "median_return_pct": _valid_number(
                        item.get("median_return_pct"), f"{name}_{label}_median_return_pct"
                    ),
                    "median_excess_return_pct": _valid_number(
                        item.get("median_excess_return_pct"), f"{name}_{label}_median_excess_return_pct"
                    ),
                    "coverage_pct": _valid_number(item.get("coverage_pct"), f"{name}_{label}_coverage_pct"),
                }
            else:
                window_metrics[label] = {"status": "insufficient_evidence"}
        rows.append({
            "sector": name,
            "classification": classification,
            "weighted_excess_return_pct": score,
            "relative_strength_rank_pct": rank,
            "membership_coverage_pct": detail.get("membership_coverage_pct"),
            "windows": window_metrics,
        })
    rows.sort(key=lambda item: (
        item["relative_strength_rank_pct"] is None,
        -(item["relative_strength_rank_pct"] or 0),
        item["sector"],
    ))
    return {
        "status": "observed",
        "as_of_session": decision_session,
        "mode": "descriptive_only",
        "method": "median_constituent_return_vs_nepse",
        "sector_coverage_pct": rotation["sector_coverage_pct"],
        "scored_sector_count": rotation.get("scored_sector_count"),
        "expected_sector_count": rotation.get("sector_count"),
        "weights": rotation.get("weights"),
        "ranked_sectors": rows,
        "signals_enabled": False,
        "broker_flow_inferred": False,
        "official_sector_index_claim": False,
        "probability": None,
    }

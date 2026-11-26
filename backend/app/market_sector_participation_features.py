"""Evidence-gated cross-sector participation component for market health."""
from __future__ import annotations

import math

DIGEST_LENGTH = 64
REQUIRED_WINDOWS = ("1M", "3M")


def _provenance(item: object, label: str, decision_session: str) -> str | None:
    if not isinstance(item, dict):
        return f"{label}_missing"
    if item.get("status") != "verified":
        return f"{label}_not_verified"
    if item.get("as_of_session") != decision_session:
        return f"{label}_as_of_session_mismatch"
    source_id = item.get("source_id")
    digest = str(item.get("source_payload_sha256", "")).lower()
    if not isinstance(source_id, str) or not source_id.strip():
        return f"{label}_source_id_missing"
    if len(digest) != DIGEST_LENGTH or any(ch not in "0123456789abcdef" for ch in digest):
        return f"{label}_source_hash_invalid"
    return None


def _finite_return(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def market_sector_participation_component(
    sector_features: dict,
    *,
    sector_universe_provenance: dict,
    price_evidence: dict,
    decision_session: str,
    minimum_sector_coverage: float = 0.80,
) -> dict:
    """Score the share of sectors with positive 1M and 3M median returns.

    Sector returns must come from the existing median-constituent sector
    strength engine. Universe and price-evidence manifests independently bind
    the point-in-time sector cohort and underlying prices to the decision date.
    """
    if not isinstance(decision_session, str) or not decision_session.strip():
        raise ValueError("decision_session must be a nonblank session date")
    if (isinstance(minimum_sector_coverage, bool)
            or not isinstance(minimum_sector_coverage, (int, float))
            or not 0 < minimum_sector_coverage <= 1):
        raise ValueError("minimum_sector_coverage must be in (0, 1]")

    reasons = {}
    for name, item in (
        ("sector_universe", sector_universe_provenance),
        ("price_evidence", price_evidence),
    ):
        reason = _provenance(item, name, decision_session)
        if reason:
            reasons[name] = reason
    if reasons:
        return {
            "status": "insufficient_evidence", "reason": "sector_input_provenance_invalid",
            "score": None, "as_of_session": decision_session, "withheld_reasons": reasons,
        }

    if not isinstance(sector_features, dict):
        raise ValueError("sector_features must be an object")
    if (sector_features.get("status") != "observed"
            or sector_features.get("as_of_session") != decision_session
            or sector_features.get("method") != "median_constituent_return_cross_sector_percentile"):
        return {
            "status": "insufficient_evidence", "reason": "sector_strength_output_not_observed_or_stale",
            "score": None, "as_of_session": decision_session,
        }
    sectors = sector_features.get("sectors")
    expected_count = sector_universe_provenance.get("expected_sector_count")
    if isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count < 1:
        return {
            "status": "insufficient_evidence", "reason": "expected_sector_count_invalid",
            "score": None, "as_of_session": decision_session,
        }
    if not isinstance(sectors, dict) or not sectors:
        return {
            "status": "insufficient_evidence", "reason": "sector_strength_results_missing",
            "score": None, "as_of_session": decision_session,
        }
    if len(sectors) != expected_count:
        return {
            "status": "insufficient_evidence", "reason": "sector_result_count_mismatch",
            "score": None, "as_of_session": decision_session,
            "expected_sector_count": expected_count, "observed_sector_count": len(sectors),
        }

    observed = {window: [] for window in REQUIRED_WINDOWS}
    missing = {window: [] for window in REQUIRED_WINDOWS}
    for sector, detail in sorted(sectors.items()):
        if not isinstance(sector, str) or not sector.strip() or not isinstance(detail, dict):
            raise ValueError("sector results must map nonblank names to objects")
        windows = detail.get("windows")
        if not isinstance(windows, dict):
            for window in REQUIRED_WINDOWS:
                missing[window].append(sector)
            continue
        for window in REQUIRED_WINDOWS:
            item = windows.get(window)
            if not isinstance(item, dict) or item.get("status") != "observed":
                missing[window].append(sector)
                continue
            value = _finite_return(item.get("median_return_pct"), f"{sector} {window} median_return_pct")
            observed[window].append({"sector": sector, "return_pct": value})

    coverage = {
        window: len(observed[window]) / expected_count
        for window in REQUIRED_WINDOWS
    }
    if any(value < minimum_sector_coverage for value in coverage.values()):
        return {
            "status": "insufficient_evidence", "reason": "sector_return_coverage_below_threshold",
            "score": None, "as_of_session": decision_session,
            "expected_sector_count": expected_count,
            "observed_sector_count": {window: len(observed[window]) for window in REQUIRED_WINDOWS},
            "coverage_pct": {window: round(value * 100, 2) for window, value in coverage.items()},
            "missing_sectors": missing,
        }

    positive = {
        window: sum(item["return_pct"] > 0 for item in observed[window])
        for window in REQUIRED_WINDOWS
    }
    participation_pct = {
        window: positive[window] / len(observed[window]) * 100
        for window in REQUIRED_WINDOWS
    }
    score = 0.60 * participation_pct["1M"] + 0.40 * participation_pct["3M"]
    warnings = []
    if participation_pct["1M"] < 30 and participation_pct["3M"] < 30:
        warnings.append("broad_sector_participation_weak")
    if participation_pct["1M"] >= 70 and participation_pct["3M"] >= 70:
        warnings.append("broad_sector_participation_strong")
    return {
        "status": "verified", "score": round(score, 2),
        "as_of_session": decision_session,
        "source_id": sector_universe_provenance["source_id"],
        "source_payload_sha256": str(sector_universe_provenance["source_payload_sha256"]).lower(),
        "price_source_id": price_evidence["source_id"],
        "price_source_payload_sha256": str(price_evidence["source_payload_sha256"]).lower(),
        "expected_sector_count": expected_count,
        "observed_sector_count": {window: len(observed[window]) for window in REQUIRED_WINDOWS},
        "coverage_pct": {window: round(value * 100, 2) for window, value in coverage.items()},
        "metrics": {
            "positive_sector_count": positive,
            "positive_sector_participation_pct": {
                window: round(value, 2) for window, value in participation_pct.items()
            },
            "weights": {"1M": 0.60, "3M": 0.40},
            "sector_returns": {
                window: observed[window] for window in REQUIRED_WINDOWS
            },
        },
        "warnings": warnings,
        "interpretation": "rules_based_positive_sector_participation_not_a_probability",
        "limitations": [
            "Uses median constituent returns, not official NEPSE sector indices",
            "Requires verified point-in-time sector membership and price evidence",
            "At least 80% of expected sectors must have observed 1M and 3M returns",
            "Does not infer broker rotation, turnover expansion or stock-level buy signals",
            "Synthetic tests validate logic only; no live sector participation score is claimed",
        ],
    }

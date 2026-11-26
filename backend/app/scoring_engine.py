"""Coverage-aware composite scoring and capital-preservation decision gate.

Component values are upstream, evidence-backed scores on a 0-100 scale.
This module does not create technical signals or infer missing evidence.
"""
from __future__ import annotations

from math import isfinite
from typing import Any

COMPONENT_WEIGHTS = {
    "wyckoff": 25,
    "trend": 25,
    "relative_strength": 15,
    "broker": 10,
    "volume": 10,
    "liquidity": 5,
    "sector": 5,
    "smc": 5,
}
TOTAL_WEIGHT = sum(COMPONENT_WEIGHTS.values())

RATING_BANDS = (
    (95, "Elite Opportunity"),
    (90, "Potential Market Leader"),
    (85, "Strong Buy Candidate"),
    (80, "Buy Watchlist"),
    (70, "Developing Setup"),
    (60, "Monitor"),
    (0, "Ignore"),
)


def _score_value(name: str, value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name}: score must be numeric, not boolean")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: score must be numeric or None") from exc
    if not isfinite(number) or not 0 <= number <= 100:
        raise ValueError(f"{name}: score must be finite and between 0 and 100")
    return number


def rating_for(score: float | None) -> str:
    if score is None:
        return "Unrated"
    for floor, label in RATING_BANDS:
        if score >= floor:
            return label
    return "Ignore"


def score_scan(
    components: dict[str, Any],
    *,
    stage1_quality: str,
    structure_confirmed: bool,
    liquidity_ok: bool,
    market_tradeable: bool,
    reward_risk: float | None,
    hard_blocks: list[str] | None = None,
) -> dict:
    """Score only supplied components and enforce strict BUY prerequisites.

    Coverage is the sum of weights for non-null components. The weighted score
    is normalized over available weights, while coverage remains separately
    visible. Missing values are never imputed as zero or neutral.

    A BUY requires complete component coverage, HIGH Stage-1 quality, confirmed
    structure, executable liquidity, a tradeable market, >=2R reward/risk and
    no hard-block flags. This is intentionally stricter than the rating band.
    """
    if not isinstance(components, dict):
        raise ValueError("components must be an object")
    unknown = sorted(set(components) - set(COMPONENT_WEIGHTS))
    if unknown:
        raise ValueError(f"unknown score components: {', '.join(unknown)}")
    if stage1_quality not in {"HIGH", "MEDIUM", "LOW"}:
        raise ValueError("stage1_quality must be HIGH, MEDIUM, or LOW")
    for name, flag in (
        ("structure_confirmed", structure_confirmed),
        ("liquidity_ok", liquidity_ok),
        ("market_tradeable", market_tradeable),
    ):
        if not isinstance(flag, bool):
            raise ValueError(f"{name} must be boolean")
    if reward_risk is not None:
        if isinstance(reward_risk, bool):
            raise ValueError("reward_risk must be numeric or None")
        try:
            reward_risk = float(reward_risk)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("reward_risk must be numeric or None") from exc
        if not isfinite(reward_risk) or reward_risk < 0:
            raise ValueError("reward_risk must be finite and non-negative")
    if hard_blocks is None:
        hard_blocks = []
    if not isinstance(hard_blocks, list) or any(
        not isinstance(item, str) or not item.strip() for item in hard_blocks
    ):
        raise ValueError("hard_blocks must be a list of nonblank strings")

    normalized = {
        name: _score_value(name, components.get(name))
        for name in COMPONENT_WEIGHTS
    }
    available_weight = sum(
        COMPONENT_WEIGHTS[name]
        for name, value in normalized.items()
        if value is not None
    )
    weighted_total = sum(
        value * COMPONENT_WEIGHTS[name]
        for name, value in normalized.items()
        if value is not None
    )
    composite = weighted_total / available_weight if available_weight else None
    coverage = available_weight / TOTAL_WEIGHT * 100
    missing = [
        name for name, value in normalized.items() if value is None
    ]

    if coverage < 80:
        coverage_status = "insufficient"
    elif coverage < 100:
        coverage_status = "provisional"
    else:
        coverage_status = "complete"

    rating = rating_for(composite)
    if coverage_status == "insufficient":
        rating = "Unrated — insufficient component coverage"
    elif coverage_status == "provisional":
        rating = f"Provisional — {rating}"

    blockers = []
    if stage1_quality != "HIGH":
        blockers.append(f"stage1_quality_{stage1_quality.lower()}")
    if coverage_status != "complete":
        blockers.append(f"component_coverage_{coverage_status}")
    if not structure_confirmed:
        blockers.append("structure_not_confirmed")
    if not liquidity_ok:
        blockers.append("liquidity_not_verified")
    if not market_tradeable:
        blockers.append("market_not_tradeable")
    if reward_risk is None or reward_risk < 2:
        blockers.append("reward_risk_below_2R_or_unavailable")
    blockers.extend(f"hard_block:{item}" for item in hard_blocks)

    if coverage_status == "insufficient" or stage1_quality == "LOW" or hard_blocks:
        action = "NO_TRADE"
    elif composite is not None and composite >= 80 and not blockers:
        action = "BUY"
    else:
        action = "WAIT"

    return {
        "composite_score": round(composite, 2) if composite is not None else None,
        "rating": rating,
        "action": action,
        "component_scores": normalized,
        "component_weights": dict(COMPONENT_WEIGHTS),
        "available_weight": available_weight,
        "coverage_pct": round(coverage, 2),
        "coverage_status": coverage_status,
        "missing_components": missing,
        "stage1_quality": stage1_quality,
        "reward_risk": round(reward_risk, 3) if reward_risk is not None else None,
        "buy_blockers": blockers,
        "probability": None,
        "probability_note": "Not estimated; a component score is not a calibrated probability.",
        "policy": "v3_capital_preservation_complete_coverage_high_quality_confirmed_setup_min_2R",
    }

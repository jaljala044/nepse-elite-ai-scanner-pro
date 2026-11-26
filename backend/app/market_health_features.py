"""Evidence-gated market health and regime classification."""
from __future__ import annotations
from math import isfinite

COMPONENT_WEIGHTS = {"trend": 25, "breadth": 25, "turnover": 20,
                     "sector_participation": 15, "volatility": 15}
TOTAL_WEIGHT = sum(COMPONENT_WEIGHTS.values())


def _valid_score(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} score must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} score must be numeric") from exc
    if not isfinite(number) or not 0 <= number <= 100:
        raise ValueError(f"{label} score must be finite and between 0 and 100")
    return number


def _verified_component(name, item, decision_session):
    if not isinstance(item, dict):
        return None, "missing_component"
    if item.get("status") != "verified":
        return None, "component_not_verified"
    if item.get("as_of_session") != decision_session:
        return None, "as_of_session_mismatch"
    source_id = item.get("source_id")
    digest = str(item.get("source_payload_sha256", "")).lower()
    if not isinstance(source_id, str) or not source_id.strip():
        return None, "source_id_missing"
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return None, "source_payload_hash_invalid"
    return _valid_score(item.get("score"), name), None


def _regime(trend, breadth, turnover, score):
    if trend < 35 and breadth < 35:
        return "markdown", "preserve_capital"
    if trend < 45 and breadth < 45:
        return "correction", "preserve_capital"
    if trend >= 65 and breadth >= 60 and turnover >= 55 and score >= 65:
        return "bull", "trade_selectively_to_aggressively"
    if trend >= 60 and breadth >= 50 and turnover >= 55:
        return "markup", "trade_selectively"
    if trend >= 50 and breadth < 50 and score >= 45:
        return "distribution", "reduce_risk_and_wait"
    if trend >= 45 and breadth >= 40 and score >= 50:
        return "accumulation", "selective_early_setups_only"
    if score < 45:
        return "distribution", "reduce_risk_and_wait"
    return "sideways", "trade_selectively_or_preserve_capital"


def market_health_features(components: dict, *, decision_session: str,
                           minimum_coverage_pct: float = 80.0) -> dict:
    """Score verified market inputs; scores are descriptors, not probabilities.

    All components must be point-in-time validated upstream. Each item needs
    status='verified', score, matching as_of_session, source_id and SHA-256.
    """
    if not isinstance(components, dict):
        raise ValueError("components must be an object")
    if not isinstance(decision_session, str) or not decision_session.strip():
        raise ValueError("decision_session must be a nonblank session date")
    if (isinstance(minimum_coverage_pct, bool)
            or not isinstance(minimum_coverage_pct, (int, float))
            or not 0 < minimum_coverage_pct <= 100):
        raise ValueError("minimum_coverage_pct must be in (0, 100]")

    scores, missing, reasons = {}, [], {}
    for name in COMPONENT_WEIGHTS:
        value, reason = _verified_component(name, components.get(name), decision_session)
        scores[name] = round(value, 4) if value is not None else None
        if reason:
            missing.append(name)
            reasons[name] = reason

    available_weight = sum(COMPONENT_WEIGHTS[name] for name, value in scores.items()
                           if value is not None)
    coverage = available_weight / TOTAL_WEIGHT * 100
    weighted = sum(scores[name] * COMPONENT_WEIGHTS[name]
                   for name in COMPONENT_WEIGHTS if scores[name] is not None)
    health = weighted / available_weight if available_weight else None
    enough_coverage = coverage >= minimum_coverage_pct
    required = ("trend", "breadth", "turnover")
    regime_ready = enough_coverage and all(scores[name] is not None for name in required)

    if regime_ready:
        regime, posture = _regime(scores["trend"], scores["breadth"],
                                  scores["turnover"], health)
    else:
        regime, posture = "unknown", "preserve_capital"

    confidence = "HIGH" if coverage == 100 else ("MEDIUM" if enough_coverage else "LOW")
    return {
        "status": "observed" if regime_ready else "insufficient_evidence",
        "decision_session": decision_session,
        "market_health_score": round(health, 2) if health is not None else None,
        "regime": regime, "trading_posture": posture, "confidence": confidence,
        "coverage_pct": round(coverage, 2),
        "coverage_status": "complete" if coverage == 100 else (
            "provisional" if enough_coverage else "insufficient"),
        "component_scores": scores, "component_weights": dict(COMPONENT_WEIGHTS),
        "missing_components": missing, "withheld_reasons": reasons,
        "probability": None,
        "limitations": [
            "Component scores must be independently validated and point-in-time filtered",
            "No missing component is imputed as neutral",
            "Market regime is a rules-based classification, not a forecast",
            "No BUY approval or position sizing is produced",
        ],
    }

"""Evidence-gated framework for the 15 concepts in the supplied IDPAT image.

This is an integration registry, not a claim to reproduce proprietary IDPAT rules.
Unknown concepts deliberately remain UNKNOWN until source definitions are supplied.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .scanner import quality_errors
from .idpat_v3 import research_features

CONCEPTS = (
    (1, "Reading Price Correctly", "ohlcv_price_context"),
    (2, "Smart Money Hidden Levels", "causal_liquidity_zone_context"),
    (3, "Trading Using Correct Timeframe", "multitimeframe_context"),
    (4, "OPR and Using Techniques", "source_definition_required"),
    (5, "OPS and Using Techniques", "source_definition_required"),
    (6, "Candle Stick Pattern That Nobody Uses", "pattern_definition_required"),
    (7, "Finding of Accumulation and Distribution", "wyckoff_hypothesis"),
    (8, "Accumulation and Distribution With Volume", "vsa_volume_context"),
    (9, "Trading With Price Structure", "causal_market_structure"),
    (10, "Trend Change in Market and Bending With The Trend", "market_sector_trend_context"),
    (11, "How To Avoid Being In The Wrong Trend", "trend_risk_guard"),
    (12, "Special: How Not To Read Candle Sticks.", "anti_pattern_definition_required"),
    (13, "Shakeout And Climax Trading Technique", "shakeout_climax_candidate"),
    (14, "Binding Price and Timeframe", "price_timeframe_confluence"),
    (15, "More Additions", "future_source_definition_required"),
)


def _as_of(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    value = rows[-1].get("date")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value) if value is not None else None


def evaluate_idpat_method(
    rows: list[dict[str, Any]],
    *,
    eligible: bool = False,
    upstream: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a non-scoring, coverage-aware IDPAT concept map.

    Eligibility must be set only by the caller's source/session gates.
    Upstream objects are evidence references; this function does not infer
    broker intent, hidden orders, accumulation or distribution.
    """
    upstream = upstream or {}
    result: dict[str, Any] = {
        "method": "idpat_15_concept_framework_v1",
        "status": "eligibility_unverified",
        "as_of": _as_of(rows),
        "score": None,
        "action": "NO TRADE",
        "concepts": [],
        "upstream": {},
        "limitations": [
            "The supplied image lists concept names but does not define proprietary rules.",
            "No IDPAT score, probability, BUY or SELL recommendation is generated.",
            "This module does not replace or alter existing scanner component scores.",
        ],
    }
    if not eligible:
        result["concepts"] = [
            {"number": n, "name": name, "key": key, "status": "UNKNOWN",
             "reason": "source_and_session_eligibility_not_verified"}
            for n, name, key in CONCEPTS
        ]
        return result

    errors = quality_errors(rows)
    if errors:
        result["status"] = "data_quality_failed"
        result["limitations"].extend(errors)
        result["concepts"] = [
            {"number": n, "name": name, "key": key, "status": "UNKNOWN",
             "reason": "ohlcv_quality_failed"}
            for n, name, key in CONCEPTS
        ]
        return result

    features = research_features(rows)
    result["research_features"] = features
    result["status"] = features["status"]
    available = {
        "ohlcv_price_context": features["status"] == "research_features_ready",
        "causal_liquidity_zone_context": "smc" in upstream,
        "multitimeframe_context": "multitimeframe" in upstream,
        "wyckoff_hypothesis": "wyckoff" in upstream,
        "vsa_volume_context": "vsa" in upstream,
        "causal_market_structure": "market_structure" in upstream,
        "market_sector_trend_context": (
            "market_regime" in upstream and "sector_rotation" in upstream
        ),
        "trend_risk_guard": (
            "minervini" in upstream and "market_regime" in upstream
        ),
        "shakeout_climax_candidate": (
            features["status"] == "research_features_ready" and "vsa" in upstream
        ),
        "price_timeframe_confluence": (
            "zone_lifecycle" in upstream and "multitimeframe" in upstream
        ),
    }
    concepts = []
    for number, name, key in CONCEPTS:
        if key.endswith("_required"):
            status, reason = "UNKNOWN", "original_IDPAT_operational_definition_missing"
        elif key == "future_source_definition_required":
            status, reason = "UNKNOWN", "source_has_no_further_definition"
        elif available.get(key, False):
            status, reason = "evidence_available_no_IDPAT_rule_applied", None
        else:
            status, reason = "UNKNOWN", "required_upstream_evidence_unavailable"
        concepts.append({
            "number": number, "name": name, "key": key,
            "status": status, "reason": reason,
        })
    result["concepts"] = concepts
    result["upstream"] = {
        key: {"status": value.get("status", "UNKNOWN"),
              "as_of": value.get("as_of"),
              "method": value.get("method")}
        for key, value in upstream.items()
    }
    result["coverage"] = {
        "listed_concepts": len(CONCEPTS),
        "evidence_available": sum(
            item["status"] == "evidence_available_no_IDPAT_rule_applied"
            for item in concepts
        ),
        "unknown": sum(item["status"] == "UNKNOWN" for item in concepts),
    }
    result["status"] = (
        "research_framework_only"
        if features["status"] == "research_features_ready"
        else features["status"]
    )
    return result

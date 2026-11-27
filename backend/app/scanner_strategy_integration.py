"""Adapters from the existing point-in-time feature pipeline into six strategy inputs.

Only observed numeric feature outputs with separate verified provenance are admitted.
Unsupported/partial outputs stay missing; this module never manufactures scores.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.scanner_strategy_lab import STRATEGIES

# One-to-one adapters only. Deliberately no aliases between correlated concepts:
# e.g. Wyckoff is not copied into accumulation_distribution, nor SMC into BOS.
FEATURE_SOURCE_MAP = {
    "trend": "trend",
    "relative_strength": "relative_strength",
    "wyckoff": "wyckoff",
    "volume": "volume",
    "smc": "smc",
    "liquidity": "liquidity",
    "sector": "sector",
    "broker_flow": "broker",
}

def _time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _score(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() and Decimal("0") <= result <= Decimal("100") else None


def adapt_feature_snapshot_to_strategy_evidence(
    *, feature_snapshot, evidence_manifest, decision_time=None
):
    """Return strategy-shaped evidence for each symbol without filling gaps.

    evidence_manifest shape:
      {symbol: {feature_name: {status, source_id, evidence_id, available_at}}}

    The manifest must be assembled from the caller's trusted evidence ledger.
    Feature outputs must have status='observed' and a numeric 0..100 score.
    """
    if not isinstance(feature_snapshot, dict):
        raise ValueError("feature_snapshot_required")
    cutoff = _time(decision_time or feature_snapshot.get("decision_time"))
    if cutoff is None:
        raise ValueError("decision_time_must_be_timezone_aware")
    bundles = feature_snapshot.get("component_feature_bundles")
    if not isinstance(bundles, dict):
        raise ValueError("component_feature_bundles_required")
    manifests = evidence_manifest if isinstance(evidence_manifest, dict) else {}

    result = {}
    for raw_symbol, bundle in bundles.items():
        symbol = str(raw_symbol).strip().upper()
        if not symbol or not isinstance(bundle, dict):
            continue
        symbol_manifest = manifests.get(symbol, {})
        if not isinstance(symbol_manifest, dict):
            symbol_manifest = {}
        by_strategy = {}
        for strategy_id, spec in STRATEGIES.items():
            strategy_evidence = {}
            missing = []
            for strategy_feature in spec["weights"]:
                source_feature = FEATURE_SOURCE_MAP.get(strategy_feature)
                feature = bundle.get(source_feature) if source_feature else None
                provenance = symbol_manifest.get(strategy_feature)
                if not isinstance(feature, dict) or not isinstance(provenance, dict):
                    missing.append(strategy_feature)
                    continue
                score = _score(feature.get("score"))
                available = _time(provenance.get("available_at"))
                if (
                    feature.get("status") != "observed"
                    or provenance.get("status") != "verified"
                    or score is None
                    or not isinstance(provenance.get("source_id"), str)
                    or not provenance["source_id"].strip()
                    or not isinstance(provenance.get("evidence_id"), str)
                    or not provenance["evidence_id"].strip()
                    or available is None
                    or available > cutoff
                ):
                    missing.append(strategy_feature)
                    continue
                strategy_evidence[strategy_feature] = {
                    "score": str(score),
                    "status": "verified",
                    "source_id": provenance["source_id"],
                    "evidence_id": provenance["evidence_id"],
                    "available_at": available.isoformat(),
                    "feature_source": source_feature,
                }
            by_strategy[strategy_id] = {
                "feature_evidence": strategy_evidence,
                "missing_features": missing,
                "admitted_feature_count": len(strategy_evidence),
                "required_feature_count": len(spec["weights"]),
            }
        result[symbol] = by_strategy

    return {
        "schema_version": "strategy-feature-adapter-1.0.0",
        "decision_time": cutoff.isoformat(),
        "symbols": result,
        "policy": "observed_numeric_feature_plus_independent_verified_provenance_required",
        "production_enabled": False,
        "limitations": [
            "The adapter does not calculate technical indicators or infer missing scores.",
            "IDPAT partial price-volume outputs are not promoted to a complete IDPAT score.",
            "Broker persistence, accumulation/distribution, hidden levels and fundamentals remain unavailable unless independently implemented and evidenced.",
            "SMC outputs marked experimental_only are not admitted as verified numeric scores.",
            "The caller is responsible for sourcing evidence_manifest from trusted server-side records, not client attestations.",
        ],
    }

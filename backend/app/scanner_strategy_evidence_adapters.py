"""Strategy-specific adapters for independently sourced, point-in-time evidence."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

FEATURES = {
    "trend_momentum": ("trend", "relative_strength", "wyckoff", "volume", "smc", "liquidity", "sector"),
    "idpat_smart_money": ("idpat_price_volume", "accumulation_distribution", "hidden_levels", "wyckoff", "volume", "broker_flow", "liquidity", "smc"),
    "broker_footprint": ("broker_flow", "broker_persistence", "price_confirmation", "distribution_risk", "sector", "liquidity"),
    "smc_ict_liquidity": ("market_structure", "liquidity_sweeps", "order_blocks", "fvg", "premium_discount", "volume", "relative_strength", "liquidity"),
    "hybrid_consensus": ("trend", "relative_strength", "wyckoff", "idpat_price_volume", "accumulation_distribution", "broker_flow", "market_structure", "liquidity_sweeps", "volume", "liquidity"),
    "fundamental_investment": ("valuation", "earnings_quality", "balance_sheet", "corporate_actions", "sector", "relative_strength", "trend", "liquidity"),
}

def _time(value):
    if not isinstance(value, str): return None
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _valid(item, cutoff):
    if not isinstance(item, dict) or item.get("status") != "verified": return False
    if not all(isinstance(item.get(k), str) and item[k].strip() for k in ("source_id", "evidence_id")): return False
    available = _time(item.get("available_at"))
    if available is None or available > cutoff: return False
    try: score = Decimal(str(item.get("score")))
    except (InvalidOperation, TypeError, ValueError): return False
    return score.is_finite() and Decimal("0") <= score <= Decimal("100")

def adapt_strategy_evidence(*, strategy_id, source_evidence, decision_cutoff):
    """Project canonical evidence into one strategy schema; never fill missing features."""
    if strategy_id not in FEATURES: raise ValueError("unsupported_strategy")
    cutoff = _time(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(source_evidence, dict): raise ValueError("source_evidence_must_be_mapping")
    adapted, withheld = {}, {}
    for feature in FEATURES[strategy_id]:
        item = source_evidence.get(feature)
        if _valid(item, cutoff):
            adapted[feature] = dict(item)
        else:
            reason = "missing" if item is None else "unverified_or_invalid_or_future_dated"
            withheld[feature] = reason
    expected = len(FEATURES[strategy_id])
    coverage = len(adapted) / expected
    return {
        "schema_version": "strategy-evidence-adapter-1.0.0",
        "strategy_id": strategy_id,
        "decision_cutoff": cutoff.isoformat(),
        "evidence": adapted,
        "withheld": withheld,
        "feature_count": expected,
        "verified_feature_count": len(adapted),
        "coverage_pct": str(Decimal(len(adapted)) * Decimal("100") / Decimal(expected)),
        "status": "complete" if not withheld else "partial",
        "policy": "No imputation, cross-strategy score substitution, future evidence or inferred verification.",
        "production_enabled": False,
    }

def adapt_all_strategy_evidence(*, source_evidence, decision_cutoff):
    return {strategy: adapt_strategy_evidence(strategy_id=strategy,
        source_evidence=source_evidence, decision_cutoff=decision_cutoff)
        for strategy in FEATURES}

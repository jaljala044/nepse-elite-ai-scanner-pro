"""Evidence-gated sector context for six scanner strategies and four horizons.

This module annotates research outputs only. Sector returns never increase a
strategy score, authorize a recommendation, or stand in for broker/fundamental
evidence. The 6–24 month investment horizon is deliberately withheld because
the verified sector rotation engine currently covers only through six months.
"""
from __future__ import annotations

from datetime import date

STRATEGIES = (
    "trend_momentum",
    "idpat_smart_money",
    "broker_footprint",
    "smc_ict_liquidity",
    "hybrid_consensus",
    "fundamental_investment",
)
HORIZONS = ("t_plus_2", "swing", "positional", "investment")
WINDOWS_BY_HORIZON = {
    "t_plus_2": ("1W",),
    "swing": ("1W", "1M"),
    "positional": ("1M", "3M"),
    "investment": ("3M", "6M"),
}
VALID_CLASSIFICATIONS = {"Leading", "Improving", "Neutral", "Weakening", "Lagging"}
STRATEGY_EVIDENCE_REQUIREMENTS = {
    "trend_momentum": ("price_structure",),
    "idpat_smart_money": ("price_structure", "supply_demand_confirmation"),
    "broker_footprint": ("independently_verified_broker_flow",),
    "smc_ict_liquidity": ("price_structure", "liquidity_confirmation"),
    "hybrid_consensus": ("independent_strategy_confluence",),
    "fundamental_investment": ("fundamental_and_corporate_action_evidence",),
}


def _digest(value: object) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _membership(symbol: str, record: object, as_of: str) -> str | None:
    if not isinstance(record, dict) or record.get("status") != "verified":
        return None
    if not isinstance(record.get("source_id"), str) or not record["source_id"].strip():
        return None
    if not _digest(record.get("source_payload_sha256")):
        return None
    try:
        start = date.fromisoformat(record["effective_from"]).isoformat()
        end = date.fromisoformat(record["effective_to"]).isoformat() if record.get("effective_to") else None
    except (KeyError, TypeError, ValueError):
        return None
    if start > as_of or (end is not None and as_of > end):
        return None
    sector = record.get("sector_code")
    return sector if isinstance(sector, str) and sector.strip() else None


def _sector_context(rotation: dict, sector: str, horizon: str) -> dict:
    detail = rotation["sectors"].get(sector)
    if not isinstance(detail, dict):
        return {"status": "insufficient_evidence", "reason": "sector_missing_from_rotation"}
    if detail.get("score_status") != "observed" or detail.get("classification") not in VALID_CLASSIFICATIONS:
        return {"status": "insufficient_evidence", "reason": "sector_score_or_classification_unverified"}
    selected = WINDOWS_BY_HORIZON[horizon]
    windows = detail.get("windows")
    if not isinstance(windows, dict):
        return {"status": "insufficient_evidence", "reason": "sector_windows_missing"}
    values = {}
    for label in selected:
        item = windows.get(label)
        if not isinstance(item, dict) or item.get("status") != "observed":
            return {"status": "insufficient_evidence", "reason": f"{label}_window_unavailable"}
        try:
            value = float(item["median_excess_return_pct"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return {"status": "insufficient_evidence", "reason": f"{label}_relative_return_invalid"}
        if value != value or value in (float("inf"), float("-inf")):
            return {"status": "insufficient_evidence", "reason": f"{label}_relative_return_non_finite"}
        values[label] = round(value, 4)
    if all(value > 0 for value in values.values()):
        alignment = "supportive"
    elif all(value < 0 for value in values.values()):
        alignment = "headwind"
    else:
        alignment = "mixed"
    return {
        "status": "observed",
        "sector": sector,
        "classification": detail["classification"],
        "relative_strength_rank_pct": detail.get("relative_strength_rank_pct"),
        "weighted_excess_return_pct": detail.get("weighted_excess_return_pct"),
        "horizon_windows": values,
        "alignment": alignment,
        "score_adjustment": 0,
        "recommendation_override": False,
    }


def build_strategy_horizon_sector_context(
    symbol: str,
    rotation: dict,
    *,
    symbol_sector_membership: dict,
    decision_session: str,
) -> dict:
    """Build 24 descriptive contexts; unknown membership/data stays withheld."""
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("symbol_required")
    try:
        as_of = date.fromisoformat(decision_session).isoformat()
    except (TypeError, ValueError):
        raise ValueError("decision_session_must_be_iso_date") from None
    if not isinstance(rotation, dict):
        raise ValueError("rotation_must_be_object")
    if (rotation.get("status") != "observed"
            or rotation.get("mode") != "descriptive_only"
            or rotation.get("as_of_session") != as_of):
        return {
            "status": "insufficient_evidence", "symbol": normalized,
            "as_of_session": as_of, "strategies": {},
            "reason": "rotation_not_observed_or_session_mismatch",
            "signals_enabled": False,
        }
    source_ids = rotation.get("source_ids")
    if (not isinstance(source_ids, dict)
            or not isinstance(source_ids.get("stocks"), list) or not source_ids["stocks"]
            or not isinstance(source_ids.get("benchmark"), list) or not source_ids["benchmark"]):
        return {
            "status": "insufficient_evidence", "symbol": normalized,
            "as_of_session": as_of, "strategies": {},
            "reason": "rotation_source_lineage_missing", "signals_enabled": False,
        }
    sector = _membership(normalized, symbol_sector_membership.get(normalized), as_of)
    if sector is None:
        return {
            "status": "insufficient_evidence", "symbol": normalized,
            "as_of_session": as_of, "strategies": {},
            "reason": "effective_dated_symbol_sector_membership_unverified",
            "signals_enabled": False,
        }

    strategies = {}
    for strategy in STRATEGIES:
        horizons = {}
        for horizon in HORIZONS:
            context = _sector_context(rotation, sector, horizon)
            if horizon == "investment":
                context = {
                    "status": "insufficient_evidence",
                    "reason": "verified_sector_history_stops_at_6M_but_investment_horizon_is_6_to_24M",
                    "required_additional_windows": ["12M", "24M"],
                    "score_adjustment": 0,
                    "recommendation_override": False,
                }
            horizons[horizon] = {
                "sector_context": context,
                "strategy_evidence_requirements": list(STRATEGY_EVIDENCE_REQUIREMENTS[strategy]),
                "strategy_specific_evidence_status": "not_supplied_by_sector_rotation",
                "action": "NO_CHANGE",
                "score_adjustment": 0,
                "recommendation_override": False,
            }
        strategies[strategy] = horizons

    # Broker-sector price alignment is not a broker footprint observation.
    strategies["broker_footprint"]["t_plus_2"]["strategy_specific_evidence_status"] = "broker_flow_unavailable"
    strategies["broker_footprint"]["swing"]["strategy_specific_evidence_status"] = "broker_flow_unavailable"
    strategies["broker_footprint"]["positional"]["strategy_specific_evidence_status"] = "broker_flow_unavailable"
    return {
        "status": "observed_descriptive",
        "symbol": normalized,
        "sector": sector,
        "as_of_session": as_of,
        "strategies": strategies,
        "sector_context_only": True,
        "signals_enabled": False,
        "score_adjustments_enabled": False,
        "recommendation_overrides_enabled": False,
        "limitations": [
            "Sector context is descriptive and does not authorize BUY, SELL or HOLD.",
            "Strategy-specific evidence must be independently validated by each strategy engine.",
            "Broker footprint cannot be inferred from sector price returns.",
            "Investment horizon is withheld until verified 12M and 24M sector windows exist.",
        ],
    }

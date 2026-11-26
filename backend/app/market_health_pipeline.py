"""Orchestrate evidence-gated NEPSE market-health components.

This module intentionally accepts explicit point-in-time evidence manifests.
It does not discover, promote, or infer verified sources on behalf of callers.
"""
from __future__ import annotations

from app.market_breadth_features import market_breadth_component
from app.market_health_features import market_health_features
from app.market_index_trend_features import nepse_index_trend_component
from app.market_sector_participation_features import market_sector_participation_component
from app.market_turnover_features import nepse_market_turnover_component
from app.market_volatility_features import nepse_index_volatility_component


def build_market_health_snapshot(
    *,
    index_rows: list[dict],
    equity_ohlcv_rows: list[dict],
    market_summary_rows: list[dict],
    session_dates: list[str],
    expected_symbols: list[str],
    equity_universe_provenance: dict,
    sector_features: dict,
    sector_universe_provenance: dict,
    sector_price_evidence: dict,
    decision_time: str,
    minimum_coverage_pct: float = 80.0,
) -> dict:
    """Build the five-component market-health snapshot for the latest session.

    All input data must already be sourced and supplied with immutable,
    point-in-time provenance. The component adapters independently validate
    record-level provenance, exact session coverage and availability cutoffs.
    """
    if not isinstance(session_dates, list) or not session_dates:
        raise ValueError("session_dates must be a nonempty canonical session list")
    decision_session = session_dates[-1]

    trend = nepse_index_trend_component(
        index_rows, session_dates=session_dates, decision_time=decision_time
    )
    breadth = market_breadth_component(
        equity_ohlcv_rows,
        expected_symbols=expected_symbols,
        universe_provenance=equity_universe_provenance,
        session_dates=session_dates,
        decision_time=decision_time,
    )
    turnover = nepse_market_turnover_component(
        market_summary_rows,
        session_dates=session_dates,
        decision_time=decision_time,
    )
    volatility = nepse_index_volatility_component(
        index_rows, session_dates=session_dates, decision_time=decision_time
    )
    sector_participation = market_sector_participation_component(
        sector_features,
        sector_universe_provenance=sector_universe_provenance,
        price_evidence=sector_price_evidence,
        decision_session=decision_session,
    )

    components = {
        "trend": trend,
        "breadth": breadth,
        "turnover": turnover,
        "sector_participation": sector_participation,
        "volatility": volatility,
    }
    health = market_health_features(
        components,
        decision_session=decision_session,
        minimum_coverage_pct=minimum_coverage_pct,
    )
    return {
        "status": health["status"],
        "decision_session": decision_session,
        "market_health": health,
        "components": components,
        "data_quality": {
            "all_components_verified": all(
                item.get("status") == "verified" for item in components.values()
            ),
            "verified_component_count": sum(
                item.get("status") == "verified" for item in components.values()
            ),
            "required_component_count": len(components),
            "production_data_claim": False,
            "note": "Component status reflects supplied evidence only; synthetic tests do not establish live source verification.",
        },
        "policy": "fail_closed_unknown_and_preserve_capital_when_market_regime_evidence_is_insufficient",
    }

"""Fail-closed, uncalibrated NEPSE broker-flow pattern candidates.

This module separates deterministic pattern flags from AI interpretation.
It requires verified NEPSE price/index/sector/breadth/liquidity/circuit context;
missing context yields INSUFFICIENT_EVIDENCE, never a guessed signal.
"""
from __future__ import annotations

import math
import re
from datetime import datetime


RULE_VERSION = "nepse-broker-flow-candidate-v1"
REQUIRED_CONTEXT_COMPONENTS = (
    "price", "nepse_index", "sector_index", "market_breadth",
    "turnover_liquidity", "circuit_context", "corporate_actions",
)


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _find_channel(window: dict, broker_code: str) -> dict | None:
    for item in window.get("execution_channels", []):
        if item.get("execution_channel_code") == broker_code:
            return item
    return None


def evaluate_broker_early_pattern(*, broker_code: str, symbol: str,
                                  execution_channel_windows: dict,
                                  market_context: dict,
                                  decision_time: str,
                                  as_of_session: str,
                                  minimum_daily_flow_multiple: float) -> dict:
    """Evaluate a transparent candidate using complete broker windows and context.

    Context must be supplied by separately verified NEPSE market-data pipelines.
    This initial rule is explicitly uncalibrated and cannot authorize a trade.
    """
    if not isinstance(broker_code, str) or not broker_code.strip():
        raise ValueError("broker_code is required")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol is required")
    cutoff = _aware(decision_time, "decision_time")
    try:
        as_of_session = datetime.fromisoformat(as_of_session).date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of_session must be YYYY-MM-DD") from exc
    if isinstance(minimum_daily_flow_multiple, bool) or not isinstance(minimum_daily_flow_multiple, (int, float)) or not math.isfinite(minimum_daily_flow_multiple) or minimum_daily_flow_multiple <= 0:
        raise ValueError("minimum_daily_flow_multiple must be finite and positive")
    if cutoff.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kathmandu")).date().isoformat() != as_of_session:
        return _insufficient(broker_code, symbol, "decision_time_session_mismatch")
    if not isinstance(execution_channel_windows, dict) or not isinstance(market_context, dict):
        raise ValueError("broker windows and market_context must be objects")

    required = ("1D", "1W", "1M")
    missing_windows = [name for name in required if name not in execution_channel_windows]
    if missing_windows:
        return _insufficient(broker_code, symbol, "missing_broker_horizons", missing_windows)

    context_missing = [
        key for key in ("status", "symbol", "as_of_session", "available_at",
                        "source_id", "source_payload_sha256",
                        "price_extension_status", "component_statuses")
        if key not in market_context
    ]
    if context_missing:
        return _insufficient(broker_code, symbol, "missing_nepse_market_context", context_missing)
    if market_context.get("status") != "verified":
        return _insufficient(broker_code, symbol, "nepse_market_context_not_verified")
    if market_context.get("as_of_session") != as_of_session:
        return _insufficient(broker_code, symbol, "market_context_session_mismatch")
    if str(market_context.get("symbol", "")).strip().upper() != symbol.strip().upper():
        return _insufficient(broker_code, symbol, "market_context_symbol_mismatch")
    if market_context.get("price_extension_status") not in {"not_extended", "extended"}:
        return _insufficient(broker_code, symbol, "price_extension_context_unavailable")
    components = market_context.get("component_statuses")
    if not isinstance(components, dict):
        return _insufficient(broker_code, symbol, "market_context_components_missing")
    unverified = [name for name in REQUIRED_CONTEXT_COMPONENTS if components.get(name) != "verified"]
    if unverified:
        return _insufficient(broker_code, symbol, "unverified_nepse_context_components", unverified)
    if not isinstance(market_context.get("source_id"), str) or not market_context["source_id"].strip():
        return _insufficient(broker_code, symbol, "market_context_source_missing")
    digest = str(market_context.get("source_payload_sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        return _insufficient(broker_code, symbol, "market_context_lineage_invalid")
    try:
        context_available = _aware(market_context["available_at"], "market_context.available_at")
    except ValueError:
        return _insufficient(broker_code, symbol, "market_context_availability_invalid")
    if context_available > cutoff:
        return _insufficient(broker_code, symbol, "market_context_not_available_at_decision_time")

    selected = {}
    for horizon in required:
        window = execution_channel_windows[horizon]
        if not isinstance(window, dict) or window.get("status") != "observed" or window.get("window_complete") is not True:
            return _insufficient(broker_code, symbol, "broker_horizon_incomplete", [horizon])
        coverage = window.get("coded_amount_coverage_pct")
        if isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or not math.isfinite(coverage) or coverage < 80:
            return _insufficient(broker_code, symbol, "broker_execution_code_coverage_below_80_pct", [horizon])
        profile = _find_channel(window, broker_code)
        if profile is None:
            return _insufficient(broker_code, symbol, "execution_channel_not_observed", [horizon])
        if profile.get("identity_status") != "execution_channel_only":
            return _insufficient(broker_code, symbol, "execution_channel_identity_boundary_missing", [horizon])
        if profile.get("prior_20_session_count") != 20:
            return _insufficient(broker_code, symbol, "insufficient_20_session_baseline", [horizon])
        selected[horizon] = profile

    daily = selected["1D"]
    weekly = selected["1W"]
    monthly = selected["1M"]
    entry_pattern = (
        daily.get("flow_class") == "net_buyer"
        and weekly.get("flow_class") == "net_buyer"
        and monthly.get("flow_class") == "net_buyer"
        and isinstance(daily.get("latest_buy_vs_prior_20_avg_ratio"), (int, float))
        and daily["latest_buy_vs_prior_20_avg_ratio"] >= minimum_daily_flow_multiple
        and market_context["price_extension_status"] == "not_extended"
    )
    exit_pattern = (
        daily.get("flow_class") == "net_seller"
        and weekly.get("flow_class") == "net_buyer"
        and monthly.get("flow_class") == "net_buyer"
        and isinstance(daily.get("latest_sell_vs_prior_20_avg_ratio"), (int, float))
        and daily["latest_sell_vs_prior_20_avg_ratio"] >= minimum_daily_flow_multiple
        and market_context["price_extension_status"] == "extended"
    )
    if entry_pattern:
        status = "EARLY_ENTRY_CANDIDATE"
        reason = "execution-channel net-buy pattern persists across daily, weekly and monthly windows while verified price context is not extended"
    elif exit_pattern:
        status = "EARLY_EXIT_RISK"
        reason = "daily execution-channel flow has reversed to net selling while weekly/monthly flow remains net buying and verified price context is extended"
    else:
        status = "WATCH"
        reason = "required cross-horizon early-entry or early-exit pattern is not present"

    return {
        "status": status,
        "symbol": symbol.strip().upper(),
        "execution_channel_code": broker_code,
        "identity_status": "execution_channel_only",
        "as_of_session": market_context["as_of_session"],
        "decision_time": cutoff.isoformat(),
        "rule_id": RULE_VERSION,
        "calibration_status": "uncalibrated_research_rule",
        "minimum_daily_flow_multiple": minimum_daily_flow_multiple,
        "confidence": None,
        "horizon_flow": {
            horizon: {
                "flow_class": selected[horizon]["flow_class"],
                "buy_amount": selected[horizon]["buy_amount"],
                "sell_amount": selected[horizon]["sell_amount"],
                "net_amount": selected[horizon]["net_amount"],
                "gross_participation_pct": selected[horizon]["gross_participation_pct"],
                "active_sessions": selected[horizon]["active_sessions"],
                "latest_buy_vs_prior_20_avg_ratio": selected[horizon]["latest_buy_vs_prior_20_avg_ratio"],
                "latest_sell_vs_prior_20_avg_ratio": selected[horizon]["latest_sell_vs_prior_20_avg_ratio"],
            }
            for horizon in required
        },
        "market_context": {
            "price_extension_status": market_context["price_extension_status"],
            "component_statuses": components,
            "source_id": market_context["source_id"],
            "source_payload_sha256": digest,
            "available_at": context_available.isoformat(),
        },
        "observed_facts_are_execution_channel_activity_only": True,
        "beneficial_ownership_or_intent_inferred": False,
        "production_recommendations_enabled": False,
        "reason": reason,
    }


def _insufficient(broker_code: str, symbol: str, reason: str,
                  missing: list[str] | None = None) -> dict:
    return {
        "status": "INSUFFICIENT_EVIDENCE",
        "symbol": symbol.strip().upper() if isinstance(symbol, str) else symbol,
        "execution_channel_code": broker_code,
        "identity_status": "execution_channel_only",
        "rule_id": RULE_VERSION,
        "calibration_status": "uncalibrated_research_rule",
        "confidence": None,
        "reason": reason,
        "missing_or_ineligible_inputs": missing or [],
        "production_recommendations_enabled": False,
    }

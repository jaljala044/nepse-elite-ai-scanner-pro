"""Point-in-time gated bridge from raw observations to descriptive features."""
from __future__ import annotations

from app.point_in_time import build_as_of_snapshot
from app.footprint_features import market_breadth, security_footprint, broker_participation_summary, broker_footprint_features
from app.trend_features import minervini_trend_template
from app.volume_vsa_features import volume_vsa_features
from app.wyckoff_features import wyckoff_event_features
from app.smc_features import smc_features
from app.sector_strength_features import sector_strength_features
from app.liquidity_features import liquidity_tradability_features
from app.scoring_engine import score_feature_bundle
from app.relative_strength_features import relative_strength_universe


def build_feature_snapshot(records: list[dict], decision_time: str,
                           expected_symbols: list[str] | None = None,
                           sector_membership: dict | None = None,
                           expected_sector_members: dict | None = None,
                           session_dates: list[str] | None = None) -> dict:
    """Filter every input by availability before deriving any feature."""
    snapshot = build_as_of_snapshot(records, decision_time)
    rows = snapshot["records"]
    prices = [r for r in rows if r.get("record_type") == "ohlcv"]
    broker_rows = [r for r in rows if r.get("record_type") == "broker"]
    by_symbol = {}
    for row in prices:
        by_symbol.setdefault(str(row.get("symbol", "")).upper(), []).append(row)
    security_features = {
        symbol: security_footprint(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
    }
    trend_features = {}
    for symbol, items in sorted(by_symbol.items()):
        if not symbol:
            continue
        required_ohlc = ("session_date", "close", "high", "low")
        missing_rows = [
            index for index, item in enumerate(items)
            if any(key not in item or item[key] is None for key in required_ohlc)
        ]
        if missing_rows:
            trend_features[symbol] = {
                "status": "insufficient_evidence",
                "reason": "required_ohlc_fields_missing",
                "missing_row_count": len(missing_rows),
                "history_sessions": len(items),
                "score": None,
                "checks": {},
            }
        else:
            trend_features[symbol] = minervini_trend_template(items)
    volume_features = {
        symbol: volume_vsa_features(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
    }
    wyckoff_features = {
        symbol: wyckoff_event_features(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
    }
    smc_features_by_symbol = {}
    for symbol, items in sorted(by_symbol.items()):
        if not symbol:
            continue
        required_smc_ohlc = ("session_date", "open", "high", "low", "close")
        missing_smc_rows = [index for index, item in enumerate(items)
                            if any(key not in item or item[key] is None for key in required_smc_ohlc)]
        if missing_smc_rows:
            smc_features_by_symbol[symbol] = {
                "status": "insufficient_evidence",
                "reason": "required_ohlc_fields_missing",
                "missing_row_count": len(missing_smc_rows),
                "history_sessions": len(items),
                "timeframes": {}, "fvg": [], "liquidity_sweeps": [], "score": None,
            }
        else:
            smc_features_by_symbol[symbol] = smc_features(items)
    broker_footprint = broker_footprint_features(broker_rows)
    if expected_symbols:
        expected_rs_symbols = [str(symbol).strip().upper() for symbol in expected_symbols]
        benchmark_rows = [
            row for row in rows
            if row.get("record_type") == "index_ohlcv"
            and str(row.get("index_code", "")).upper() == "NEPSE"
        ]
        relative_strength = relative_strength_universe(
            {symbol: by_symbol.get(symbol, []) for symbol in expected_rs_symbols},
            benchmark_rows,
            expected_symbols=expected_rs_symbols,
        )
    else:
        relative_strength = {
            "status": "insufficient_evidence",
            "reason": "expected_equity_universe_not_supplied",
            "eligible_symbols": 0,
            "expected_symbols": 0,
            "results": {},
        }
    if sector_membership is not None and expected_sector_members is not None and session_dates is not None:
        sector_features = sector_strength_features(
            prices, sector_membership=sector_membership,
            expected_sector_members=expected_sector_members,
            session_dates=session_dates,
        )
    else:
        sector_features = {
            "status": "insufficient_evidence",
            "reason": "verified_sector_membership_and_calendar_not_supplied",
            "sectors": {},
        }
    if expected_symbols is not None and session_dates is not None:
        liquidity_snapshot = liquidity_tradability_features(
            prices, expected_symbols=expected_symbols, session_dates=session_dates,
        )
    else:
        liquidity_snapshot = {
            "status": "insufficient_evidence",
            "reason": "expected_universe_and_canonical_calendar_not_supplied",
            "symbols": {},
        }
    component_candidates = {}
    component_feature_bundles = {}
    for symbol in sorted(by_symbol):
        if not symbol:
            continue
        rs_item = relative_strength.get("results", {}).get(symbol, {})
        broker_item = broker_footprint.get("security_features", {}).get(symbol, {}).get("1W", {})
        liquidity_item = liquidity_snapshot.get("symbols", {}).get(symbol, {})
        sector_code = (
            sector_membership.get(symbol, {}).get("sector_code")
            if isinstance(sector_membership, dict)
            and isinstance(sector_membership.get(symbol), dict)
            and sector_membership.get(symbol, {}).get("status") == "verified"
            else None
        )
        sector_item = sector_features.get("sectors", {}).get(sector_code, {}) if sector_code else {}

        # Preserve complete upstream evidence objects. The scoring adapter
        # accepts only status='observed' plus a numeric score; unavailable,
        # partial and experimental outputs remain missing.
        feature_bundle = {
            "wyckoff": wyckoff_features[symbol],
            "trend": trend_features[symbol],
            "relative_strength": {
                "status": rs_item.get("score_status", "insufficient_evidence"),
                "score": rs_item.get("score"),
                "as_of_session": rs_item.get("as_of_session"),
                "rank": rs_item.get("rank"),
            },
            "broker": broker_item,
            "volume": volume_features[symbol],
            "liquidity": liquidity_item,
            "sector": {
                "status": sector_item.get("score_status", "insufficient_evidence"),
                "score": sector_item.get("score"),
                "sector_code": sector_code,
                "score_coverage_pct": sector_item.get("score_coverage_pct"),
            },
            "smc": smc_features_by_symbol[symbol],
        }
        component_feature_bundles[symbol] = feature_bundle
        component_candidates[symbol] = {
            name: (
                feature.get("score")
                if isinstance(feature, dict) and feature.get("status") == "observed"
                else None
            )
            for name, feature in feature_bundle.items()
        }

    aggregate_scores = {}
    for symbol, feature_bundle in component_feature_bundles.items():
        aggregate_scores[symbol] = score_feature_bundle(
            feature_bundle,
            stage1_quality="UNKNOWN",
            structure_confirmed=False,
            liquidity_ok=False,
            market_tradeable=False,
            reward_risk=None,
            hard_blocks=[
                "stage1_hard_gates_not_connected",
                "horizon_trade_plan_not_available",
                "market_regime_gate_not_connected",
            ],
        )
        aggregate_scores[symbol]["decision_status"] = "research_only_fail_closed_stage2_preview"

    latest_by_symbol = []
    for symbol, items in by_symbol.items():
        latest = sorted(items, key=lambda r: (r.get("session_date", ""), r.get("available_at", "")))[-1]
        latest_by_symbol.append(latest)
    return {
        "decision_time": snapshot["decision_time"],
        "included_input_count": snapshot["included_count"],
        "excluded_input_count": snapshot["excluded_count"],
        "max_input_available_at": snapshot["max_input_available_at"],
        "point_in_time_eligible": snapshot["point_in_time_eligible"],
        "market_breadth": market_breadth(latest_by_symbol, expected_symbols),
        "security_features": security_features,
        "trend_features": trend_features,
        "volume_features": volume_features,
        "wyckoff_features": wyckoff_features,
        "smc_features": smc_features_by_symbol,
        "component_candidates": component_candidates,
        "component_feature_bundles": component_feature_bundles,
        "aggregate_scores": aggregate_scores,
        "relative_strength": relative_strength,
        "broker_participation": broker_participation_summary(broker_rows),
        "broker_footprint": broker_footprint,
        "sector_strength": sector_features,
        "liquidity_tradability": liquidity_snapshot,
        "interpretation": "descriptive_only_not_a_trading_signal",
    }

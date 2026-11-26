"""Point-in-time gated bridge from raw observations to descriptive features."""
from __future__ import annotations

from app.point_in_time import build_as_of_snapshot
from app.footprint_features import market_breadth, security_footprint, broker_participation_summary
from app.trend_features import minervini_trend_template
from app.volume_vsa_features import volume_vsa_features
from app.wyckoff_features import wyckoff_event_features
from app.smc_features import smc_features


def build_feature_snapshot(records: list[dict], decision_time: str,
                           expected_symbols: list[str] | None = None) -> dict:
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
    smc_features_by_symbol = {
        symbol: smc_features(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
    }
    component_candidates = {}
    for symbol in sorted(by_symbol):
        if not symbol:
            continue
        component_candidates[symbol] = {
            "wyckoff": wyckoff_features[symbol].get("score") if wyckoff_features[symbol].get("status") == "observed" else None,
            "trend": trend_features[symbol].get("score") if trend_features[symbol].get("status") == "observed" else None,
            "relative_strength": None,
            "broker": None,
            "volume": volume_features[symbol].get("score") if volume_features[symbol].get("status") == "observed" else None,
            "liquidity": None,
            "sector": None,
            "smc": smc_features_by_symbol[symbol].get("score") if smc_features_by_symbol[symbol].get("status") == "observed" else None,
        }
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
        "broker_participation": broker_participation_summary(broker_rows),
        "interpretation": "descriptive_only_not_a_trading_signal",
    }

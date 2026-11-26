"""Point-in-time gated bridge from raw observations to descriptive features."""
from __future__ import annotations

from app.point_in_time import build_as_of_snapshot
from app.footprint_features import market_breadth, security_footprint, broker_participation_summary
from app.trend_features import minervini_trend_template


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
    trend_features = {
        symbol: minervini_trend_template(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
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
        "broker_participation": broker_participation_summary(broker_rows),
        "interpretation": "descriptive_only_not_a_trading_signal",
    }

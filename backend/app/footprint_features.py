"""Transparent, coverage-aware footprint feature primitives.

These functions calculate descriptive statistics only. They do not infer intent
or issue buy/sell signals. Inputs must already be point-in-time filtered.
"""
from __future__ import annotations

from math import sqrt


def market_breadth(rows: list[dict], expected_symbols: list[str] | None = None) -> dict:
    latest = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        if symbol and row.get("close") is not None and row.get("previous_close") is not None:
            latest[symbol] = row
    advancing = declining = unchanged = 0
    for row in latest.values():
        close, previous = float(row["close"]), float(row["previous_close"])
        if close > previous:
            advancing += 1
        elif close < previous:
            declining += 1
        else:
            unchanged += 1
    eligible = len(expected_symbols) if expected_symbols is not None else len(latest)
    observed = len(latest)
    return {
        "advancing": advancing, "declining": declining, "unchanged": unchanged,
        "observed_symbols": observed, "eligible_symbols": eligible,
        "coverage_ratio": observed / eligible if eligible else None,
        "advance_decline_ratio": advancing / declining if declining else None,
        "status": "insufficient_coverage" if not eligible or observed < eligible else "observed",
    }


def security_footprint(rows: list[dict], minimum_history: int = 5) -> dict:
    ordered = sorted(rows, key=lambda r: r["session_date"])
    if not ordered:
        return {"status": "insufficient_evidence", "reason": "no_rows"}
    current = ordered[-1]
    close = float(current["close"])
    previous = float(current["previous_close"]) if current.get("previous_close") is not None else None
    volume = float(current["volume"])
    historical_volumes = [float(r["volume"]) for r in ordered[:-1][-minimum_history:]]
    baseline = sum(historical_volumes) / len(historical_volumes) if historical_volumes else None
    return {
        "status": "observed" if previous and baseline is not None and len(historical_volumes) >= minimum_history else "insufficient_evidence",
        "session_date": current["session_date"],
        "close": close,
        "return_pct": ((close / previous) - 1) * 100 if previous else None,
        "volume": volume,
        "prior_volume_mean": baseline,
        "volume_ratio": volume / baseline if baseline and baseline > 0 else None,
        "history_sessions": len(historical_volumes),
        "interpretation": "descriptive_price_volume_observation_only",
    }


def broker_participation_summary(rows: list[dict]) -> dict:
    """Summarize only verified broker entities; expose unmapped share separately."""
    mapped = [r for r in rows if r.get("identity_status") == "verified" and r.get("broker_entity_id")]
    unknown = [r for r in rows if r not in mapped]
    buy = sum(float(r.get("amount", 0)) for r in mapped if r.get("side") == "buy")
    sell = sum(float(r.get("amount", 0)) for r in mapped if r.get("side") == "sell")
    total = buy + sell
    return {
        "verified_broker_rows": len(mapped),
        "unmapped_or_unverified_rows": len(unknown),
        "unverified_row_share": len(unknown) / len(rows) if rows else None,
        "verified_buy_amount": buy,
        "verified_sell_amount": sell,
        "verified_net_amount": buy - sell,
        "status": "insufficient_evidence" if not mapped else "partial_identity_coverage" if unknown else "observed",
    }

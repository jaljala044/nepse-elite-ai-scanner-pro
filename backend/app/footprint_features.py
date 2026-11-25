"""Transparent, coverage-aware footprint feature primitives.

These functions calculate descriptive statistics only. They do not infer intent
or issue buy/sell signals. Inputs must already be point-in-time filtered.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import date
import math


def market_breadth(rows: list[dict], expected_symbols: list[str] | None = None) -> dict:
    latest = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        if symbol and row.get("close") is not None and row.get("previous_close") is not None:
            latest[symbol] = row
    advancing = declining = unchanged = 0
    for symbol, row in latest.items():
        try:
            close, previous = float(row["close"]), float(row["previous_close"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{symbol}: close and previous_close must be numeric") from exc
        if not math.isfinite(close) or not math.isfinite(previous) or close <= 0 or previous <= 0:
            raise ValueError(f"{symbol}: close and previous_close must be finite and positive")
        if close > previous:
            advancing += 1
        elif close < previous:
            declining += 1
        else:
            unchanged += 1
    if expected_symbols is not None:
        normalized_expected = [str(symbol).strip().upper() for symbol in expected_symbols]
        if any(not symbol for symbol in normalized_expected):
            raise ValueError("expected_symbols cannot contain blank values")
        if len(normalized_expected) != len(set(normalized_expected)):
            raise ValueError("expected_symbols must be unique")
        eligible = len(normalized_expected)
    else:
        eligible = len(latest)
    observed = len(latest)
    return {
        "advancing": advancing, "declining": declining, "unchanged": unchanged,
        "observed_symbols": observed, "eligible_symbols": eligible,
        "coverage_ratio": observed / eligible if eligible else None,
        "advance_decline_ratio": advancing / declining if declining else None,
        "status": "insufficient_coverage" if not eligible or observed < eligible else "observed",
    }


def security_footprint(rows: list[dict], minimum_history: int = 5) -> dict:
    if not isinstance(minimum_history, int) or minimum_history < 1:
        raise ValueError("minimum_history must be a positive integer")
    ordered = sorted(rows, key=lambda r: r["session_date"])
    if not ordered:
        return {"status": "insufficient_evidence", "reason": "no_rows"}
    session_dates = []
    for index, row in enumerate(ordered):
        try:
            session_dates.append(date.fromisoformat(str(row["session_date"])).isoformat())
            close_value = float(row["close"])
            volume_value = float(row["volume"])
            previous_value = float(row["previous_close"]) if row.get("previous_close") is not None else None
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"security footprint row {index}: invalid date or numeric field") from exc
        if (not math.isfinite(close_value) or close_value <= 0
                or not math.isfinite(volume_value) or volume_value < 0
                or (previous_value is not None and (not math.isfinite(previous_value) or previous_value <= 0))):
            raise ValueError(f"security footprint row {index}: prices must be finite positive and volume finite non-negative")
    if len(session_dates) != len(set(session_dates)):
        raise ValueError("security footprint contains duplicate session dates")
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
    """Summarize verified broker flow with exact decimal amounts and explicit unknowns."""
    mapped = []
    unresolved = []
    buy = Decimal("0")
    sell = Decimal("0")
    for index, row in enumerate(rows):
        status = row.get("identity_status")
        broker_id = row.get("broker_entity_id")
        if status == "verified":
            if not broker_id:
                raise ValueError(f"row {index}: verified identity requires broker_entity_id")
            mapped.append(row)
        else:
            if broker_id is not None:
                raise ValueError(f"row {index}: unresolved identity cannot carry broker_entity_id")
            if status not in {"unmapped", "ambiguous", "rejected"}:
                raise ValueError(f"row {index}: unsupported identity_status")
            unresolved.append(row)
        if row.get("side") not in {"buy", "sell"}:
            raise ValueError(f"row {index}: side must be buy or sell")
        try:
            amount = Decimal(str(row.get("amount")))
        except (InvalidOperation, TypeError):
            raise ValueError(f"row {index}: amount must be a decimal")
        if not amount.is_finite() or amount < 0:
            raise ValueError(f"row {index}: amount must be finite and non-negative")
        if status == "verified":
            if row["side"] == "buy":
                buy += amount
            else:
                sell += amount
    total = buy + sell
    return {
        "verified_broker_rows": len(mapped),
        "unmapped_or_unverified_rows": len(unresolved),
        "unverified_row_share": len(unresolved) / len(rows) if rows else None,
        "verified_buy_amount": str(buy),
        "verified_sell_amount": str(sell),
        "verified_net_amount": str(buy - sell),
        "verified_amount_total": str(total),
        "status": "insufficient_evidence" if not mapped else "partial_identity_coverage" if unresolved else "observed",
    }

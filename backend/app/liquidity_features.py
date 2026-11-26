"""Coverage-aware, point-in-time liquidity/tradability descriptors.

A relative score is emitted only when turnover, trade frequency, quoted spread,
and displayed depth are all verified for every required session. It is not an
execution approval: order-book freshness, market impact and fill simulation
remain separate gates.
"""
from __future__ import annotations

from datetime import date
from math import isfinite

MIN_HISTORY_SESSIONS = 20
METRICS = ("turnover", "trade_count", "spread_pct", "displayed_depth")


def _day(value):
    return date.fromisoformat(str(value)).isoformat()


def _number(value, label, *, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not isfinite(result) or result < 0 or (positive and result <= 0):
        raise ValueError(f"{label} must be finite and {'positive' if positive else 'non-negative'}")
    return result


def _percentile_ranks(values, *, lower_is_better=False):
    ordered = sorted(values.values())
    result = {}
    for symbol, value in values.items():
        below = sum(x < value for x in ordered)
        equal = sum(x == value for x in ordered)
        rank = (below + 0.5 * equal) / len(ordered) * 100
        result[symbol] = 100 - rank if lower_is_better else rank
    return result


def liquidity_tradability_features(rows: list[dict], *, expected_symbols: list[str],
                                   session_dates: list[str],
                                   minimum_universe_coverage: float = 0.80) -> dict:
    """Score cross-sectional liquidity only from verified 20-session evidence.

    Each row must contain symbol, session_date, turnover, trade_count, best_bid,
    best_ask, bid_depth, ask_depth, source_validation_status, source_id and
    source_payload_sha256. Inputs must already be point-in-time filtered.
    """
    if not isinstance(rows, list) or not isinstance(expected_symbols, list):
        raise ValueError("rows and expected_symbols must be lists")
    if isinstance(minimum_universe_coverage, bool) or not isinstance(minimum_universe_coverage, (int, float)) or not 0 < minimum_universe_coverage <= 1:
        raise ValueError("minimum_universe_coverage must be in (0, 1]")
    symbols = [str(item).strip().upper() for item in expected_symbols]
    if not symbols or any(not item for item in symbols) or len(symbols) != len(set(symbols)):
        raise ValueError("expected_symbols must be unique nonblank symbols")
    if not isinstance(session_dates, list) or len(session_dates) < MIN_HISTORY_SESSIONS:
        return {"status": "insufficient_evidence", "reason": "canonical_calendar_below_20_sessions",
                "symbols": {}, "expected_symbols": len(symbols)}
    calendar = [_day(item) for item in session_dates]
    if calendar != sorted(calendar) or len(calendar) != len(set(calendar)):
        raise ValueError("session_dates must be unique and ascending")
    required_dates = calendar[-MIN_HISTORY_SESSIONS:]
    expected_fields = ("turnover", "trade_count", "best_bid", "best_ask",
                       "bid_depth", "ask_depth", "source_validation_status",
                       "source_id", "source_payload_sha256")
    grouped = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"row {index} must be an object")
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol not in symbols:
            continue
        if any(key not in row or row[key] is None for key in expected_fields):
            continue
        if row["source_validation_status"] != "verified":
            continue
        digest = str(row["source_payload_sha256"]).lower()
        if (not isinstance(row["source_id"], str) or not row["source_id"].strip()
                or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)):
            continue
        day = _day(row.get("session_date"))
        turnover = _number(row["turnover"], f"row {index} turnover")
        trade_count = _number(row["trade_count"], f"row {index} trade_count")
        bid = _number(row["best_bid"], f"row {index} best_bid", positive=True)
        ask = _number(row["best_ask"], f"row {index} best_ask", positive=True)
        bid_depth = _number(row["bid_depth"], f"row {index} bid_depth")
        ask_depth = _number(row["ask_depth"], f"row {index} ask_depth")
        if ask < bid:
            raise ValueError(f"row {index}: crossed order book")
        series = grouped.setdefault(symbol, {})
        if day in series:
            raise ValueError(f"duplicate symbol/session: {symbol} {day}")
        mid = (bid + ask) / 2
        series[day] = {
            "turnover": turnover, "trade_count": trade_count,
            "spread_pct": (ask - bid) / mid * 100,
            "displayed_depth": bid_depth + ask_depth,
        }

    metrics = {name: {} for name in METRICS}
    symbol_details = {}
    for symbol in symbols:
        series = grouped.get(symbol, {})
        if any(day not in series for day in required_dates):
            symbol_details[symbol] = {"status": "insufficient_evidence",
                "observed_sessions": sum(day in series for day in required_dates),
                "required_sessions": MIN_HISTORY_SESSIONS, "score": None,
                "missing_sessions": [day for day in required_dates if day not in series]}
            continue
        observations = [series[day] for day in required_dates]
        # Median daily turnover/trade count and median quote metrics reduce
        # sensitivity to a single closing auction or transient book snapshot.
        for metric in METRICS:
            values = sorted(item[metric] for item in observations)
            mid = len(values) // 2
            metrics[metric][symbol] = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
        symbol_details[symbol] = {"status": "observed", "observed_sessions": len(observations),
            "required_sessions": MIN_HISTORY_SESSIONS, "median_turnover": metrics["turnover"][symbol],
            "median_trade_count": metrics["trade_count"][symbol],
            "median_spread_pct": round(metrics["spread_pct"][symbol], 6),
            "median_displayed_depth": metrics["displayed_depth"][symbol], "score": None}

    observed_symbols = [symbol for symbol in symbols if symbol_details[symbol]["status"] == "observed"]
    universe_coverage = len(observed_symbols) / len(symbols)
    if len(observed_symbols) >= 2 and universe_coverage >= minimum_universe_coverage:
        ranks = {
            "turnover": _percentile_ranks(metrics["turnover"]),
            "trade_count": _percentile_ranks(metrics["trade_count"]),
            "spread_pct": _percentile_ranks(metrics["spread_pct"], lower_is_better=True),
            "displayed_depth": _percentile_ranks(metrics["displayed_depth"]),
        }
        for symbol in observed_symbols:
            component_ranks = {name: round(ranks[name][symbol], 2) for name in METRICS}
            score = sum(component_ranks.values()) / len(component_ranks)
            symbol_details[symbol]["metric_percentiles"] = component_ranks
            symbol_details[symbol]["score"] = round(score, 2)
            symbol_details[symbol]["score_status"] = "observed"
    else:
        for symbol in observed_symbols:
            symbol_details[symbol]["score_status"] = "insufficient_evidence"
    return {
        "status": "observed" if len(observed_symbols) >= 2 and universe_coverage >= minimum_universe_coverage else "insufficient_evidence",
        "as_of_session": required_dates[-1], "history_sessions": MIN_HISTORY_SESSIONS,
        "expected_symbols": len(symbols), "observed_symbols": len(observed_symbols),
        "universe_coverage_pct": round(universe_coverage * 100, 2),
        "minimum_universe_coverage_pct": round(minimum_universe_coverage * 100, 2),
        "symbols": symbol_details,
        "method": "equal_weight_cross_sectional_percentiles_turnover_trade_count_spread_depth",
        "execution_approval": False,
        "limitations": ["Relative ranking is not an absolute liquidity threshold",
                        "Daily quote snapshots do not establish intraday execution depth",
                        "No market-impact or fill simulation is performed",
                        "Missing or unverified source rows are not imputed"],
    }

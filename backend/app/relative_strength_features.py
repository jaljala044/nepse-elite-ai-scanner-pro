"""Cross-sectional relative-strength engine versus the NEPSE benchmark.

The score is a percentile rank among the supplied eligible equity universe.
It is not a probability. Stock and benchmark returns use common session dates.
"""
from __future__ import annotations

from datetime import date
import math

PERIODS = {"1w": 5, "1m": 21, "3m": 63, "6m": 126}
PERIOD_WEIGHTS = {"1w": 0.20, "1m": 0.30, "3m": 0.30, "6m": 0.20}


def _close_series(rows: list[dict], label: str) -> dict[str, float]:
    if not isinstance(rows, list):
        raise ValueError(f"{label}: rows must be a list")
    result = {}
    for i, row in enumerate(rows):
        try:
            session = date.fromisoformat(str(row["session_date"])).isoformat()
            close = float(row["close"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{label} row {i}: invalid session_date or close") from exc
        if not math.isfinite(close) or close <= 0:
            raise ValueError(f"{label} row {i}: close must be finite and positive")
        if session in result:
            raise ValueError(f"{label}: duplicate session_date {session}")
        result[session] = close
    return result


def relative_strength_universe(
    securities: dict[str, list[dict]], benchmark_rows: list[dict]
) -> dict:
    """Calculate weighted excess returns and percentile scores for eligible stocks.

    A period return is measured across N prior session intervals plus the
    current session. All four periods must be available for a stock. Benchmark
    alignment is by exact session_date; no forward-fill/interpolation occurs.
    """
    if not isinstance(securities, dict) or not securities:
        raise ValueError("securities must be a non-empty symbol-to-rows mapping")
    benchmark = _close_series(benchmark_rows, "benchmark")
    benchmark_dates = sorted(benchmark)
    raw = {}
    excluded = {}
    for symbol, rows in sorted(securities.items()):
        normalized_symbol = str(symbol).strip().upper()
        if not normalized_symbol:
            raise ValueError("security symbols cannot be blank")
        stock = _close_series(rows, normalized_symbol)
        current_date = benchmark_dates[-1] if benchmark_dates else None
        if current_date is None or current_date not in stock:
            excluded[normalized_symbol] = "missing_latest_benchmark_session"
            continue
        metrics = {}
        missing = []
        for period, intervals in PERIODS.items():
            required_dates = benchmark_dates[-(intervals + 1):]
            if len(required_dates) < intervals + 1:
                missing.append(period)
                continue
            missing_dates = [day for day in required_dates if day not in stock]
            if missing_dates:
                missing.append(period + ":missing_exact_sessions=" + str(len(missing_dates)))
                continue
            start_date = required_dates[0]
            stock_return = (stock[current_date] / stock[start_date] - 1) * 100
            benchmark_return = (
                benchmark[current_date] / benchmark[start_date] - 1
            ) * 100
            metrics[period] = {
                "stock_return_pct": round(stock_return, 4),
                "benchmark_return_pct": round(benchmark_return, 4),
                "excess_return_pct": round(stock_return - benchmark_return, 4),
                "start_session": start_date,
                "end_session": current_date,
                "intervals": intervals,
            }
        if missing:
            excluded[normalized_symbol] = "insufficient_common_history:" + ",".join(missing)
            continue
        weighted = sum(
            metrics[p]["excess_return_pct"] * PERIOD_WEIGHTS[p]
            for p in PERIODS
        )
        raw[normalized_symbol] = {
            "periods": metrics,
            "weighted_excess_return_pct": round(weighted, 4),
            "as_of_session": current_date,
            "common_sessions": len(benchmark_dates),
        }

    values = sorted(item["weighted_excess_return_pct"] for item in raw.values())
    results = {}
    n = len(values)
    for symbol, item in raw.items():
        value = item["weighted_excess_return_pct"]
        less = sum(v < value for v in values)
        equal = sum(v == value for v in values)
        percentile = ((less + (equal + 1) / 2) / n * 100) if n else None
        results[symbol] = {
            **item,
            "score": round(percentile, 2),
            "rank": 1 + sum(v > value for v in values),
            "universe_size": n,
            "interpretation": "cross_sectional_relative_strength_percentile_not_probability",
        }
    return {
        "status": "observed" if results else "insufficient_evidence",
        "benchmark_sessions": len(benchmark_dates),
        "eligible_symbols": n,
        "excluded_symbols": excluded,
        "weights": dict(PERIOD_WEIGHTS),
        "results": results,
    }

"""Point-in-time relative strength versus the verified final NEPSE index.

RS is a cross-sectional percentile of weighted excess returns, not a probability.
A symbol is eligible only when every exact benchmark session is present and
stock prices carry verified source, price-basis and corporate-action status.
"""
from __future__ import annotations

from datetime import date
import math

PERIODS = {"1w": 5, "1m": 21, "3m": 63, "6m": 126}
PERIOD_WEIGHTS = {"1w": 0.20, "1m": 0.30, "3m": 0.30, "6m": 0.20}
PRICE_BASIS_STATUSES = {"verified_unadjusted_no_actions", "verified_adjusted"}
CORPORATE_ACTION_STATUSES = {"clear", "adjusted_verified"}


def _valid_digest(value: object) -> bool:
    digest = str(value or "").lower()
    return len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)


def _close_series(rows: list[dict], label: str, *, benchmark: bool = False) -> tuple[dict[str, float], dict]:
    if not isinstance(rows, list):
        raise ValueError(f"{label}: rows must be a list")
    result = {}
    excluded = {"unverified_rows": 0, "invalid_provenance_rows": 0}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{label} row {i}: must be an object")
        if benchmark:
            admitted = (
                row.get("record_type") == "index_ohlcv"
                and str(row.get("index_code", "")).upper() == "NEPSE"
                and row.get("source_validation_status") == "verified"
                and row.get("finality_status") == "final"
            )
        else:
            admitted = (
                row.get("source_validation_status") == "verified"
                and row.get("price_basis_status") in PRICE_BASIS_STATUSES
                and row.get("corporate_action_status") in CORPORATE_ACTION_STATUSES
            )
        if not admitted:
            excluded["unverified_rows"] += 1
            continue
        if (not isinstance(row.get("source_id"), str) or not row["source_id"].strip()
                or not _valid_digest(row.get("source_payload_sha256"))):
            excluded["invalid_provenance_rows"] += 1
            continue
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
    return result, excluded


def relative_strength_universe(
    securities: dict[str, list[dict]],
    benchmark_rows: list[dict],
    *,
    expected_symbols: list[str],
    minimum_universe_coverage: float = 0.80,
) -> dict:
    """Calculate 1W/1M/3M/6M excess returns and cross-sectional percentiles.

    A period return spans N prior exchange-session intervals plus the current
    session. All four periods must be present for each symbol. A component score
    is emitted only when at least two symbols and the configured share of the
    expected equity universe qualify.
    """
    if not isinstance(securities, dict) or not isinstance(expected_symbols, list):
        raise ValueError("securities and expected_symbols must be object/list")
    if (isinstance(minimum_universe_coverage, bool)
            or not isinstance(minimum_universe_coverage, (int, float))
            or not 0 < minimum_universe_coverage <= 1):
        raise ValueError("minimum_universe_coverage must be in (0, 1]")
    symbols = [str(symbol).strip().upper() for symbol in expected_symbols]
    if not symbols or any(not symbol for symbol in symbols) or len(symbols) != len(set(symbols)):
        raise ValueError("expected_symbols must be unique nonblank symbols")

    benchmark, benchmark_excluded = _close_series(benchmark_rows, "benchmark", benchmark=True)
    benchmark_dates = sorted(benchmark)
    if len(benchmark_dates) < PERIODS["6m"] + 1:
        return {
            "status": "insufficient_evidence", "reason": "insufficient_verified_final_nepse_benchmark_history",
            "benchmark_sessions": len(benchmark_dates), "eligible_symbols": 0,
            "expected_symbols": len(symbols), "universe_coverage_pct": 0.0,
            "excluded_symbols": {symbol: "benchmark_history_below_127_sessions" for symbol in symbols},
            "benchmark_excluded": benchmark_excluded, "results": {}, "weights": dict(PERIOD_WEIGHTS),
        }

    required_dates = benchmark_dates[-(PERIODS["6m"] + 1):]
    current_date = required_dates[-1]
    raw, excluded = {}, {}
    for symbol in symbols:
        rows = securities.get(symbol)
        if not rows:
            excluded[symbol] = "missing_stock_price_rows"
            continue
        stock, stock_excluded = _close_series(rows, symbol, benchmark=False)
        if stock_excluded["unverified_rows"] or stock_excluded["invalid_provenance_rows"]:
            excluded[symbol] = "stock_price_provenance_or_price_basis_unverified"
            continue
        missing_dates = [day for day in required_dates if day not in stock]
        if missing_dates:
            excluded[symbol] = "missing_exact_benchmark_sessions:" + str(len(missing_dates))
            continue
        metrics = {}
        for period, intervals in PERIODS.items():
            dates = required_dates[-(intervals + 1):]
            start_date = dates[0]
            stock_return = (stock[current_date] / stock[start_date] - 1) * 100
            benchmark_return = (benchmark[current_date] / benchmark[start_date] - 1) * 100
            metrics[period] = {
                "stock_return_pct": round(stock_return, 4),
                "benchmark_return_pct": round(benchmark_return, 4),
                "excess_return_pct": round(stock_return - benchmark_return, 4),
                "start_session": start_date, "end_session": current_date,
                "intervals": intervals,
            }
        weighted = sum(metrics[p]["excess_return_pct"] * PERIOD_WEIGHTS[p] for p in PERIODS)
        raw[symbol] = {
            "periods": metrics, "weighted_excess_return_pct": round(weighted, 4),
            "as_of_session": current_date, "common_sessions": len(required_dates),
        }

    eligible_count = len(raw)
    coverage = eligible_count / len(symbols)
    scores_available = eligible_count >= 2 and coverage >= minimum_universe_coverage
    values = sorted(item["weighted_excess_return_pct"] for item in raw.values())
    results = {}
    for symbol, item in raw.items():
        value = item["weighted_excess_return_pct"]
        if scores_available:
            less = sum(v < value for v in values)
            equal = sum(v == value for v in values)
            percentile = (less + (equal + 1) / 2) / eligible_count * 100
            rank = 1 + sum(v > value for v in values)
            score = round(percentile, 2)
        else:
            rank, score = None, None
        results[symbol] = {
            **item, "score": score, "rank": rank, "universe_size": eligible_count,
            "score_status": "observed" if scores_available else "insufficient_evidence",
            "interpretation": "cross_sectional_relative_strength_percentile_not_probability",
        }
    return {
        "status": "observed" if scores_available else "insufficient_evidence",
        "reason": None if scores_available else "eligible_universe_coverage_or_cross_section_too_small",
        "benchmark_sessions": len(benchmark_dates), "eligible_symbols": eligible_count,
        "expected_symbols": len(symbols), "universe_coverage_pct": round(coverage * 100, 2),
        "minimum_universe_coverage_pct": round(minimum_universe_coverage * 100, 2),
        "as_of_session": current_date, "excluded_symbols": excluded,
        "benchmark_excluded": benchmark_excluded, "weights": dict(PERIOD_WEIGHTS),
        "results": results,
        "limitations": [
            "Requires independently verified final NEPSE index rows",
            "Requires verified stock source, price basis and corporate-action status",
            "No forward-fill, interpolation, stale endpoint or session substitution",
            "Percentile is relative to the supplied expected equity universe, not a probability",
        ],
    }

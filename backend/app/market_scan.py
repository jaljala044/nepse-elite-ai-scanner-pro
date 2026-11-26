"""Deterministic all-market orchestration for the research scanner.

This module deliberately does not promote candidates or rank securities. The
per-symbol callback remains responsible for existing evidence and eligibility
gates and scanner logic.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Iterable, Mapping, Sequence


def _row_date(row: Mapping) -> date:
    value = row.get("date")
    if isinstance(value, datetime):
        raise ValueError("OHLCV row date must not be a datetime")
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def run_market_scan(
    candidate_symbols: Iterable[str],
    market_data: Mapping[str, Sequence[Mapping]],
    *,
    as_of: date | None,
    scan_symbol: Callable[[str, list[dict], date | None], dict],
) -> dict:
    """Run one deterministic scan pass over the full supplied candidate set.

    Rows after as_of are excluded before the callback is invoked. Missing data
    remains an explicit outcome. No session calendar is inferred and no
    ranking or recommendation is created here.
    """
    symbols = list(candidate_symbols)
    if any(not isinstance(symbol, str) or not symbol or symbol != symbol.upper()
           for symbol in symbols):
        raise ValueError("candidate symbols must be non-empty uppercase strings")
    if len(set(symbols)) != len(symbols):
        raise ValueError("candidate symbols must be unique")

    results = []
    for symbol in sorted(symbols):
        source_rows = list(market_data.get(symbol, ()))
        rows = []
        for row in source_rows:
            day = _row_date(row)
            if as_of is None or day <= as_of:
                rows.append(dict(row))
        rows.sort(key=lambda row: _row_date(row))
        if not rows:
            results.append({
                "symbol": symbol,
                "status": "insufficient_data",
                "result_bucket": "unknown_results",
                "ranking_eligible": False,
                "buy_list_eligible": False,
                "as_of": as_of.isoformat() if as_of else None,
                "observations": 0,
                "latest_available_observation": None,
                "signals": [],
                "metrics": {},
                "limitations": ["no_ohlcv_observations_available"],
            })
            continue
        result = scan_symbol(symbol, rows, as_of)
        if not isinstance(result, dict):
            raise TypeError("scan_symbol must return a dictionary")
        result = dict(result)
        result["symbol"] = symbol
        result["requested_as_of"] = as_of.isoformat() if as_of else None
        result["latest_available_observation"] = _row_date(rows[-1]).isoformat()
        result["observations"] = len(rows)
        results.append(result)

    status_counts = {}
    for result in results:
        status = str(result.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1

    data_available = sum(result["observations"] > 0 for result in results)
    return {
        "scanner_id": "3A.01",
        "scanner_version": "0.1.0",
        "mode": "research_only",
        "as_of": as_of.isoformat() if as_of else None,
        "candidate_universe_count": len(symbols),
        "symbols_with_ohlcv": data_available,
        "symbols_without_ohlcv": len(symbols) - data_available,
        "coverage_pct": round(data_available / len(symbols) * 100, 2) if symbols else 0.0,
        "status_counts": dict(sorted(status_counts.items())),
        "results": results,
        "ranking_enabled": False,
        "disclaimer": (
            "Candidate-universe coverage is not authoritative exchange membership. "
            "Missing observations do not imply a closed session or an open session. "
            "No ranking or recommendation is produced by this orchestration layer."
        ),
    }

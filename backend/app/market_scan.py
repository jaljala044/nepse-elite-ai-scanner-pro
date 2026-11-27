"""Deterministic all-market orchestration for the research scanner.

This module deliberately does not promote candidates or rank securities. The
per-symbol callback remains responsible for existing evidence and eligibility
gates and scanner logic.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Iterable, Mapping, Sequence


def _row_date(row: Mapping) -> date:
    if not isinstance(row, Mapping):
        raise ValueError("OHLCV row must be a mapping")
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
    if isinstance(candidate_symbols, (str, bytes)):
        raise ValueError("candidate_symbols must be an iterable of symbols, not a string")
    if not isinstance(market_data, Mapping):
        raise ValueError("market_data must be a mapping keyed by symbol")
    if not callable(scan_symbol):
        raise ValueError("scan_symbol must be callable")
    if as_of is not None and (not isinstance(as_of, date) or isinstance(as_of, datetime)):
        raise ValueError("as_of must be a calendar date or None, not a datetime")
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
                "requested_as_of": as_of.isoformat() if as_of else None,
                "observations": 0,
                "latest_available_observation": None,
                "latest_observation_calendar_age_days": None,
                "freshness_status": "no_observation",
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
        # The 3A.01 orchestration layer is research-only even if a callback
        # accidentally returns permissive ranking or BUY eligibility flags.
        result["ranking_eligible"] = False
        result["buy_list_eligible"] = False
        latest_day = _row_date(rows[-1])
        result["latest_available_observation"] = latest_day.isoformat()
        result["latest_observation_calendar_age_days"] = (
            (as_of - latest_day).days if as_of is not None else None
        )
        result["freshness_status"] = "calendar_age_only_session_status_unverified"
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
        "symbols_with_observations": data_available,
        "symbols_without_observations": len(symbols) - data_available,
        "observation_coverage_pct": round(data_available / len(symbols) * 100, 2) if symbols else 0.0,
        "coverage_basis": "at_least_one_stored_ohlcv_row_not_data_quality_or_session_validation",
        "status_counts": dict(sorted(status_counts.items())),
        "results": results,
        "ranking_enabled": False,
        "disclaimer": (
            "Candidate-universe coverage is not authoritative exchange membership. "
            "Missing observations do not imply a closed session or an open session. "
            "Calendar age is descriptive only; no stale-session judgment is made without "
            "verified session-calendar evidence. No ranking or recommendation is produced."
        ),
    }

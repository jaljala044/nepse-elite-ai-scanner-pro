"""Coverage and quality audit for V3 daily OHLCV datasets.

The audit reports what is present; it never fills missing sessions or assumes
that calendar days are trading sessions. Supply an authoritative universe file
and (optionally) an exchange-session calendar for stronger completeness checks.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import isfinite
from typing import Any, Iterable

REQUIRED = ("symbol", "date", "open", "high", "low", "close", "volume")


def _date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def audit_ohlcv(
    rows: Iterable[dict[str, Any]],
    expected_symbols: Iterable[str] | None = None,
    expected_sessions: Iterable[date | str] | None = None,
    target_universe_size: int = 309,
    as_of: date | str | None = None,
) -> dict[str, Any]:
    """Return auditable per-symbol coverage and quality metrics.

    Missing sessions are measured only against an explicitly supplied session
    calendar. Without one, session gaps are deliberately not guessed.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors: list[dict[str, Any]] = []
    seen: set[tuple[str, date]] = set()
    duplicate_count = 0
    row_count = 0

    for line, source in enumerate(rows, start=1):
        row_count += 1
        try:
            symbol = str(source["symbol"]).strip().upper()
            if not symbol or len(symbol) > 20:
                raise ValueError("invalid symbol")
            session = _date(source["date"])
            values = {}
            for field in ("open", "high", "low", "close", "volume"):
                value = source[field]
                if isinstance(value, bool):
                    raise ValueError(f"{field} must be numeric")
                number = float(value)
                if not isfinite(number):
                    raise ValueError(f"{field} must be finite")
                values[field] = number
            if min(values[k] for k in ("open", "high", "low", "close")) <= 0:
                raise ValueError("prices must be positive")
            if values["volume"] < 0:
                raise ValueError("volume must be non-negative")
            if values["high"] < max(values["open"], values["close"], values["low"]):
                raise ValueError("high is below another OHLC value")
            if values["low"] > min(values["open"], values["close"], values["high"]):
                raise ValueError("low is above another OHLC value")
            key = (symbol, session)
            if key in seen:
                duplicate_count += 1
                errors.append({"row": line, "symbol": symbol, "date": session.isoformat(),
                               "error": "duplicate symbol/session key"})
                continue
            seen.add(key)
            grouped[symbol].append({"date": session, **values})
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            errors.append({"row": line, "error": str(exc)})

    expected = sorted({str(s).strip().upper() for s in (expected_symbols or []) if str(s).strip()})
    expected_set = set(expected)
    observed_set = set(grouped)
    universe = expected_set or observed_set
    calendar = sorted({_date(s) for s in expected_sessions}) if expected_sessions is not None else None
    cutoff = _date(as_of) if as_of is not None else None
    per_symbol = []
    for symbol in sorted(universe | observed_set):
        series = sorted(grouped.get(symbol, []), key=lambda x: x["date"])
        dates = [r["date"] for r in series]
        eligible_calendar = [d for d in calendar if cutoff is None or d <= cutoff] if calendar is not None else None
        present = set(dates)
        missing = sorted(set(eligible_calendar or []) - present) if eligible_calendar is not None else []
        expected_count = len(eligible_calendar) if eligible_calendar is not None else None
        latest = dates[-1] if dates else None
        stale_days = (cutoff - latest).days if cutoff and latest else None
        per_symbol.append({
            "symbol": symbol,
            "rows": len(series),
            "first_session": dates[0].isoformat() if dates else None,
            "latest_session": latest.isoformat() if latest else None,
            "calendar_sessions_expected": expected_count,
            "calendar_sessions_missing": len(missing) if eligible_calendar is not None else None,
            "missing_session_dates": [d.isoformat() for d in missing],
            "stale_calendar_days_as_of": stale_days,
            "status": "missing_symbol" if not series else (
                "calendar_gaps" if missing else "observed"
            ),
        })

    observed_count = len(observed_set)
    expected_count = len(expected_set) if expected_set else target_universe_size
    missing_symbols = sorted(expected_set - observed_set) if expected_set else []
    return {
        "audit": "nepse_v3_ohlcv_coverage",
        "row_count_input": row_count,
        "valid_unique_rows": len(seen),
        "duplicate_keys": duplicate_count,
        "invalid_rows": len(errors) - duplicate_count,
        "observed_symbols": observed_count,
        "expected_symbols": expected_count,
        "missing_symbols": missing_symbols,
        "missing_symbol_count": len(missing_symbols) if expected_set else max(0, expected_count - observed_count),
        "universe_source": "provided_master" if expected_set else "target_count_only",
        "session_calendar_supplied": calendar is not None,
        "as_of": cutoff.isoformat() if cutoff else None,
        "per_symbol": per_symbol,
        "errors": errors,
        "limitations": [
            "Without an authoritative symbol master, missing symbol names cannot be identified.",
            "Without an exchange-session calendar, missing trading sessions cannot be inferred from calendar dates.",
            "Coverage is descriptive and does not certify corporate-action adjustment or source accuracy.",
        ],
    }

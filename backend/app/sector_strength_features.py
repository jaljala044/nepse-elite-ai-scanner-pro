"""Point-in-time sector rotation features with explicit membership/session coverage.

Sector returns are cross-sectional medians of constituent returns, not official
sector indices. Membership and session calendars must be supplied by validated
upstream sources. No missing prices or constituents are imputed.
"""
from __future__ import annotations

from datetime import date
from math import isfinite

WINDOWS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126}


def _day(value: object) -> str:
    return date.fromisoformat(str(value)).isoformat()


def _positive(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return number


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def sector_strength_features(price_rows: list[dict], *, sector_membership: dict,
                             expected_sector_members: dict, session_dates: list[str],
                             minimum_member_coverage: float = 0.80) -> dict:
    """Calculate sector median returns and cross-sector percentile ranks.

    sector_membership maps symbol to verified sector/source metadata.
    expected_sector_members is the complete point-in-time security-master
    universe. session_dates is the canonical ordered exchange-session calendar.
    """
    if not isinstance(price_rows, list) or not isinstance(sector_membership, dict):
        raise ValueError("price_rows and sector_membership must be list/object")
    if not isinstance(expected_sector_members, dict) or not expected_sector_members:
        return {"status": "insufficient_evidence", "reason": "verified_sector_universe_missing",
                "sectors": {}, "windows": WINDOWS.copy()}
    if not isinstance(session_dates, list) or len(session_dates) < max(WINDOWS.values()) + 1:
        return {"status": "insufficient_evidence", "reason": "canonical_session_calendar_too_short",
                "sectors": {}, "windows": WINDOWS.copy()}
    if isinstance(minimum_member_coverage, bool) or not isinstance(minimum_member_coverage, (int, float)) or not 0 < minimum_member_coverage <= 1:
        raise ValueError("minimum_member_coverage must be in (0, 1]")

    calendar = [_day(item) for item in session_dates]
    if len(calendar) != len(set(calendar)) or calendar != sorted(calendar):
        raise ValueError("session_dates must be unique and ascending")
    normalized_members = {}
    for sector, members in expected_sector_members.items():
        if not isinstance(sector, str) or not sector.strip() or not isinstance(members, list) or not members:
            raise ValueError("expected sector membership must contain non-empty sector lists")
        normalized = [str(symbol).strip().upper() for symbol in members]
        if any(not symbol for symbol in normalized) or len(normalized) != len(set(normalized)):
            raise ValueError(f"{sector}: expected members must be unique nonblank symbols")
        normalized_members[sector] = normalized

    eligible = {}
    for symbol, record in sector_membership.items():
        normalized_symbol = str(symbol).strip().upper()
        if not normalized_symbol or not isinstance(record, dict):
            continue
        digest = str(record.get("source_payload_sha256", "")).lower()
        if (record.get("status") == "verified"
                and isinstance(record.get("source_id"), str) and record["source_id"].strip()
                and len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)
                and record.get("sector_code") in normalized_members):
            eligible[normalized_symbol] = record["sector_code"]

    prices = {}
    for index, row in enumerate(price_rows):
        if not isinstance(row, dict):
            raise ValueError(f"price row {index} must be an object")
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            raise ValueError(f"price row {index} missing symbol")
        day = _day(row.get("session_date"))
        close = _positive(row.get("close"), f"price row {index} close")
        series = prices.setdefault(symbol, {})
        if day in series:
            raise ValueError(f"duplicate symbol/session: {symbol} {day}")
        series[day] = close

    as_of = calendar[-1]
    sector_returns = {}
    sector_detail = {}
    for sector, members in sorted(normalized_members.items()):
        mapped_members = [symbol for symbol in members if eligible.get(symbol) == sector]
        windows = {}
        for label, count in WINDOWS.items():
            dates = calendar[-(count + 1):]
            start_date = dates[0]
            valid_returns, missing_symbols = [], []
            for symbol in mapped_members:
                series = prices.get(symbol, {})
                if any(day not in series for day in dates):
                    missing_symbols.append(symbol)
                    continue
                valid_returns.append((series[as_of] / series[start_date] - 1) * 100)
            coverage = len(valid_returns) / len(members) if members else 0
            observed = _median(valid_returns) if valid_returns else None
            status = "observed" if coverage >= minimum_member_coverage and observed is not None else "insufficient_evidence"
            windows[label] = {
                "median_return_pct": round(observed, 4) if observed is not None else None,
                "observed_members": len(valid_returns), "expected_members": len(members),
                "coverage_pct": round(coverage * 100, 2), "status": status,
                "missing_members": missing_symbols,
            }
            if status == "observed":
                sector_returns.setdefault(label, {})[sector] = observed
        sector_detail[sector] = {"windows": windows,
            "membership_coverage_pct": round(len(mapped_members) / len(members) * 100, 2),
            "mapped_members": len(mapped_members), "expected_members": len(members)}

    for label in WINDOWS:
        observed = sector_returns.get(label, {})
        for sector in sector_detail:
            item = sector_detail[sector]["windows"][label]
            value = item["median_return_pct"]
            if item["status"] != "observed" or len(observed) < 2:
                item["relative_rank_pct"] = None
                continue
            below = sum(1 for other in observed.values() if other < value)
            equal = sum(1 for other in observed.values() if other == value)
            item["relative_rank_pct"] = round((below + 0.5 * equal) / len(observed) * 100, 2)

    for detail in sector_detail.values():
        ranks = [detail["windows"][label]["relative_rank_pct"] for label in WINDOWS]
        available = [rank for rank in ranks if rank is not None]
        detail["score"] = round(sum(available) / len(available), 2) if len(available) == len(WINDOWS) else None
        detail["score_status"] = "observed" if detail["score"] is not None else "insufficient_evidence"
        detail["score_coverage_pct"] = round(len(available) / len(WINDOWS) * 100, 2)

    return {
        "status": "observed" if any(item["score_status"] == "observed" for item in sector_detail.values()) else "insufficient_evidence",
        "as_of_session": as_of,
        "method": "median_constituent_return_cross_sector_percentile",
        "method_note": "Not an official sector index; requires complete point-in-time membership and exact canonical sessions.",
        "windows": WINDOWS.copy(), "sector_count": len(sector_detail), "sectors": sector_detail,
        "limitations": ["No official sector index return is inferred",
                        "No broker rotation or turnover expansion is inferred",
                        "Missing constituents and missing sessions are not imputed",
                        "Scores are cross-sectional descriptors, not probabilities or trade signals"],
    }

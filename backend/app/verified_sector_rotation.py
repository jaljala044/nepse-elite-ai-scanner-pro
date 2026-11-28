"""Verified point-in-time NEPSE sector rotation intelligence.

Sector performance is a median of constituent stock returns, not an official
sector index. Membership, stock prices, benchmark prices and session calendar
must be independently validated upstream. This module emits descriptive
rotation labels only, never a trade signal.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from math import isfinite

WINDOWS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126}
WEIGHTS = {"1W": 0.20, "1M": 0.30, "3M": 0.30, "6M": 0.20}
PRICE_BASIS = {"verified_unadjusted_no_actions", "verified_adjusted"}
CORPORATE_ACTION = {"clear", "adjusted_verified"}


def _aware(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_must_be_timezone_aware")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{label}_must_be_timezone_aware") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{label}_must_be_timezone_aware")
    return result.astimezone(timezone.utc)


def _digest(value):
    value = str(value or "").lower()
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _close(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label}_must_be_positive_finite")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label}_must_be_positive_finite") from None
    if not isfinite(result) or result <= 0:
        raise ValueError(f"{label}_must_be_positive_finite")
    return result


def _median(values):
    values = sorted(values)
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def _rank(values, value):
    below = sum(item < value for item in values)
    equal = sum(item == value for item in values)
    return round((below + 0.5 * equal) / len(values) * 100, 2)


def build_verified_sector_rotation(
    stock_rows: list[dict],
    benchmark_rows: list[dict],
    *,
    expected_sector_members: dict[str, list[str]],
    sector_membership: dict[str, dict],
    verified_session_dates: list[str],
    decision_time: str,
    minimum_member_coverage: float = 0.80,
    minimum_sector_coverage: float = 0.80,
) -> dict:
    """Build sector returns, NEPSE-relative strength, breadth and leadership.

    Requires 127 exact verified exchange sessions for all four horizons. Missing
    constituent bars are not skipped or filled. Membership records must carry
    an effective date range, source ID and SHA-256 payload digest. Stock bars
    require verified price basis and corporate-action status.
    """
    cutoff = _aware(decision_time, "decision_time")
    for label, value in (("minimum_member_coverage", minimum_member_coverage),
                         ("minimum_sector_coverage", minimum_sector_coverage)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 1:
            raise ValueError(f"{label}_must_be_between_zero_and_one")

    if not isinstance(verified_session_dates, list):
        raise ValueError("verified_session_dates_must_be_a_list")
    calendar = []
    for item in verified_session_dates:
        try:
            parsed = date.fromisoformat(item).isoformat()
        except (TypeError, ValueError):
            raise ValueError("invalid_verified_session_date") from None
        if parsed != item:
            raise ValueError("verified_session_dates_must_be_iso_dates")
        calendar.append(parsed)
    if calendar != sorted(set(calendar)):
        raise ValueError("verified_session_dates_must_be_unique_ascending")
    if len(calendar) < 127:
        return {"status": "insufficient_evidence", "reason": "verified_calendar_below_127_sessions",
                "calendar_sessions": len(calendar), "sectors": {}, "signals_enabled": False}

    local_cutoff = cutoff.astimezone(timezone(timedelta(hours=5, minutes=45))).date().isoformat()
    calendar = [day for day in calendar if day <= local_cutoff]
    if len(calendar) < 127:
        return {"status": "insufficient_evidence", "reason": "calendar_before_decision_time_below_127_sessions",
                "calendar_sessions": len(calendar), "sectors": {}, "signals_enabled": False}
    calendar = calendar[-127:]
    dates_by_window = {name: calendar[-(n + 1):] for name, n in WINDOWS.items()}

    if not isinstance(expected_sector_members, dict) or not expected_sector_members:
        return {"status": "insufficient_evidence", "reason": "expected_sector_universe_missing",
                "sectors": {}, "signals_enabled": False}
    normalized_members = {}
    for sector, symbols in expected_sector_members.items():
        if not isinstance(sector, str) or not sector.strip() or not isinstance(symbols, list) or not symbols:
            raise ValueError("invalid_expected_sector_members")
        values = [str(symbol).strip().upper() for symbol in symbols]
        if any(not value for value in values) or len(values) != len(set(values)):
            raise ValueError(f"invalid_or_duplicate_sector_members:{sector}")
        normalized_members[sector] = values
    all_symbols = [symbol for members in normalized_members.values() for symbol in members]
    if len(all_symbols) != len(set(all_symbols)):
        raise ValueError("security_assigned_to_multiple_expected_sectors")

    membership = {}
    as_of = calendar[-1]
    for symbol in all_symbols:
        record = sector_membership.get(symbol)
        if not isinstance(record, dict):
            continue
        if (record.get("status") != "verified"
                or not isinstance(record.get("source_id"), str) or not record["source_id"].strip()
                or not _digest(record.get("source_payload_sha256"))):
            continue
        try:
            available = _aware(record.get("available_at"), "membership_available_at")
            start = date.fromisoformat(record.get("effective_from")).isoformat()
            end = date.fromisoformat(record["effective_to"]).isoformat() if record.get("effective_to") else None
        except (TypeError, ValueError):
            continue
        if available <= cutoff and start <= as_of and (end is None or as_of <= end):
            membership[symbol] = (record.get("sector_code"), start)

    def parse_rows(rows, benchmark=False):
        series = {}
        source_ids = set()
        excluded = {"unverified": 0, "invalid_provenance": 0, "late_or_out_of_calendar": 0}
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"price_row_{i}_must_be_an_object")
            if benchmark:
                admitted = (row.get("record_type") == "index_ohlcv"
                            and str(row.get("index_code", "")).upper() == "NEPSE"
                            and row.get("source_validation_status") == "verified"
                            and row.get("finality_status") == "final")
                key = "NEPSE"
            else:
                admitted = (row.get("source_validation_status") == "verified"
                            and row.get("price_basis_status") in PRICE_BASIS
                            and row.get("corporate_action_status") in CORPORATE_ACTION)
                key = str(row.get("symbol", "")).strip().upper()
            if not admitted:
                excluded["unverified"] += 1
                continue
            source_id = row.get("source_id")
            if not isinstance(source_id, str) or not source_id.strip() or not _digest(row.get("source_payload_sha256")):
                excluded["invalid_provenance"] += 1
                continue
            try:
                day = date.fromisoformat(str(row["session_date"])).isoformat()
                available = _aware(row.get("available_at"), "available_at")
            except (KeyError, TypeError, ValueError):
                excluded["invalid_provenance"] += 1
                continue
            if day not in calendar or available > cutoff:
                excluded["late_or_out_of_calendar"] += 1
                continue
            if not key:
                excluded["invalid_provenance"] += 1
                continue
            value = _close(row.get("close"), f"price_row_{i}_close")
            bucket = series.setdefault(key, {})
            if day in bucket:
                raise ValueError(f"duplicate_price_session:{key}:{day}")
            bucket[day] = value
            source_ids.add(source_id)
        return series, excluded, sorted(source_ids)

    stocks, stock_excluded, stock_sources = parse_rows(stock_rows)
    benchmark, benchmark_excluded, benchmark_sources = parse_rows(benchmark_rows, benchmark=True)
    benchmark = benchmark.get("NEPSE", {})
    if any(day not in benchmark for day in calendar):
        missing = [day for day in calendar if day not in benchmark]
        return {"status": "insufficient_evidence", "reason": "nepse_benchmark_missing_exact_sessions",
                "missing_benchmark_sessions": missing, "sectors": {}, "signals_enabled": False,
                "excluded_rows": {"stock": stock_excluded, "benchmark": benchmark_excluded}}

    sector_results = {}
    for sector, symbols in sorted(normalized_members.items()):
        mapped = [symbol for symbol in symbols if membership.get(symbol, (None, None))[0] == sector]
        sector_windows = {}
        weighted_excess = []
        all_window_valid = True
        for label, dates in dates_by_window.items():
            start, end = dates[0], dates[-1]
            stock_returns, excess_returns, constituents = [], [], []
            missing = sorted(set(symbols) - set(mapped))
            for symbol in mapped:
                if membership[symbol][1] > start:
                    missing.append(symbol)
                    continue
                series = stocks.get(symbol, {})
                if any(day not in series for day in dates):
                    missing.append(symbol)
                    continue
                stock_return = (series[end] / series[start] - 1) * 100
                benchmark_return = (benchmark[end] / benchmark[start] - 1) * 100
                stock_returns.append(stock_return)
                excess_returns.append(stock_return - benchmark_return)
                constituents.append({"symbol": symbol, "return_pct": round(stock_return, 4),
                                     "excess_return_pct": round(stock_return - benchmark_return, 4)})
            coverage = len(stock_returns) / len(symbols)
            observed = coverage >= minimum_member_coverage and bool(stock_returns)
            sector_windows[label] = {
                "median_return_pct": round(_median(stock_returns), 4) if observed else None,
                "nepse_return_pct": round((benchmark[end] / benchmark[start] - 1) * 100, 4),
                "median_excess_return_pct": round(_median(excess_returns), 4) if observed else None,
                "advancers": sum(value > 0 for value in stock_returns) if observed else None,
                "decliners": sum(value < 0 for value in stock_returns) if observed else None,
                "unchanged": sum(value == 0 for value in stock_returns) if observed else None,
                "observed_members": len(stock_returns), "expected_members": len(symbols),
                "coverage_pct": round(coverage * 100, 2),
                "status": "observed" if observed else "insufficient_evidence",
                "missing_members": sorted(missing),
                "constituents": sorted(constituents, key=lambda r: (-r["excess_return_pct"], r["symbol"])) if observed else None,
                "start_session": start, "end_session": end,
            }
            if observed:
                weighted_excess.append(sector_windows[label]["median_excess_return_pct"])
            else:
                all_window_valid = False
        score = sum(sector_windows[label]["median_excess_return_pct"] * WEIGHTS[label]
                    for label in WINDOWS) if all_window_valid else None
        sector_results[sector] = {
            "membership_coverage_pct": round(len(mapped) / len(symbols) * 100, 2),
            "mapped_members": len(mapped), "expected_members": len(symbols),
            "windows": sector_windows,
            "weighted_excess_return_pct": round(score, 4) if score is not None else None,
            "score_status": "observed" if score is not None else "insufficient_evidence",
        }

    scored = [item["weighted_excess_return_pct"] for item in sector_results.values()
              if item["weighted_excess_return_pct"] is not None]
    sector_coverage = len(scored) / len(sector_results) if sector_results else 0
    if len(scored) < 2 or sector_coverage < minimum_sector_coverage:
        for item in sector_results.values():
            item["relative_strength_rank_pct"] = None
            item["classification"] = "insufficient_evidence"
        status = "insufficient_evidence"
    else:
        for item in sector_results.values():
            score = item["weighted_excess_return_pct"]
            if score is None:
                item["relative_strength_rank_pct"] = None
                item["classification"] = "insufficient_evidence"
                continue
            rank = _rank(scored, score)
            item["relative_strength_rank_pct"] = rank
            one_month = item["windows"]["1M"]["median_excess_return_pct"]
            three_month = item["windows"]["3M"]["median_excess_return_pct"]
            if rank >= 75 and score > 0:
                classification = "Leading"
            elif rank >= 50 and score > 0 and one_month > 0:
                classification = "Improving"
            elif rank <= 25 and score < 0:
                classification = "Lagging"
            elif one_month < 0 or three_month < 0:
                classification = "Weakening"
            else:
                classification = "Neutral"
            item["classification"] = classification
        status = "observed"

    return {
        "status": status, "mode": "descriptive_only", "as_of_session": as_of,
        "decision_time": cutoff.isoformat(), "calendar_sessions": len(calendar),
        "sector_count": len(sector_results), "scored_sector_count": len(scored),
        "sector_coverage_pct": round(sector_coverage * 100, 2),
        "windows": dict(WINDOWS), "weights": dict(WEIGHTS),
        "sectors": sector_results,
        "source_ids": {"stocks": stock_sources, "benchmark": benchmark_sources},
        "excluded_rows": {"stock": stock_excluded, "benchmark": benchmark_excluded},
        "signals_enabled": False, "production_score": None, "probability": None,
        "limitations": [
            "Sector returns are median constituent returns, not official sector index returns.",
            "Membership must be known by cutoff and cover each measured return window; reclassified members are excluded.",
            "No missing stock or benchmark session is skipped, interpolated or forward-filled.",
            "Sector leadership is descriptive and is not a forecast or trade signal.",
            "Broker turnover rotation is a separate evidence stream and must not be inferred here.",
        ],
    }

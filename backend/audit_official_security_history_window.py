"""Validate a bounded official NEPSE per-security history capture against official date summaries.

The history endpoint is queried for current equity-candidate IDs. Missing rows remain
UNKNOWN; explicit zero-activity rows remain evidence, not NO_TRADE authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs, urlparse

OFFICIAL_HOST = "nepalstock.com.np"
HISTORY_PATH = "/api/nots/market/history/security/"
SUMMARY_SOURCE_ID = "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY"
HISTORY_SOURCE_ID = "NEPSE_OFFICIAL_PER_SECURITY_PRICE_VOLUME_HISTORY"


def _number(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"negative or nonfinite {label}: {value!r}")
    return result


def _official_url(value: object, expected_path_prefix: str) -> bool:
    parsed = urlparse(str(value or ""))
    return (
        parsed.scheme == "https"
        and parsed.hostname == OFFICIAL_HOST
        and parsed.port in (None, 443)
        and parsed.path.startswith(expected_path_prefix)
    )


def load_expected_market_dates(body_path: Path, capture_report_path: Path,
                               start_date: str, end_date: str) -> tuple[list[str], dict]:
    report = json.loads(capture_report_path.read_text(encoding="utf-8"))
    body = body_path.read_bytes()
    observed_hash = hashlib.sha256(body).hexdigest()
    if report.get("source_id") != SUMMARY_SOURCE_ID:
        raise ValueError("unexpected official market-summary source ID")
    if report.get("http_status") != 200 or report.get("response_origin_verified") is not True:
        raise ValueError("market-summary capture is not verified HTTP 200 from official origin")
    if not _official_url(report.get("source_url"), "/api/nots/market-summary-history"):
        raise ValueError("market-summary capture URL is not the approved official endpoint")
    if report.get("response_sha256") != observed_hash or report.get("response_bytes") != len(body):
        raise ValueError("market-summary raw body hash/size does not match capture report")
    payload = json.loads(body.decode("utf-8"))
    rows = payload.get("content") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("official market-summary raw body has no content list")
    dates = []
    by_date = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"market-summary row {index} is not an object")
        day = str(row.get("businessDate", ""))[:10]
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError(f"market-summary row {index} has invalid date") from exc
        if day in by_date:
            raise ValueError(f"duplicate official market-summary date {day}")
        by_date[day] = row
        if start_date <= day <= end_date:
            for key in ("totalTransactions", "totalTradedShares", "totalTurnover", "tradedScrips"):
                _number(row.get(key), f"{day} market summary {key}")
            dates.append(day)
    dates.sort()
    if not dates:
        raise ValueError("no official market-summary dates in requested window")
    return dates, {
        "source_id": report["source_id"],
        "source_url": report["source_url"],
        "retrieved_at_utc": report.get("retrieved_at_utc"),
        "response_sha256": observed_hash,
        "response_bytes": len(body),
        "date_count_in_window": len(dates),
    }


def audit_history_window(history_report_path: Path, market_body_path: Path,
                         market_capture_report_path: Path, start_date: str,
                         end_date: str, expected_equity_count: int = 281) -> dict:
    date.fromisoformat(start_date)
    date.fromisoformat(end_date)
    if start_date > end_date:
        raise ValueError("start_date must not exceed end_date")
    expected_dates, market_identity = load_expected_market_dates(
        market_body_path, market_capture_report_path, start_date, end_date
    )
    capture = json.loads(history_report_path.read_text(encoding="utf-8"))
    if capture.get("source_id") != HISTORY_SOURCE_ID:
        raise ValueError("unexpected official per-security history source ID")
    if capture.get("endpoint_path") != HISTORY_PATH + "{security_id}":
        raise ValueError("unexpected official per-security history endpoint path")
    if capture.get("requested_start_date") != start_date or capture.get("requested_end_date") != end_date:
        raise ValueError("capture window does not match requested audit window")
    if capture.get("historical_security_identity_verified") is not False:
        raise ValueError("historical identity must remain explicitly unverified")
    if capture.get("security_list_error") is not None:
        raise ValueError("official current security-list capture reported an error")
    security_events = capture.get("security_list_capture")
    if not isinstance(security_events, list) or not security_events:
        raise ValueError("official security-list response evidence is missing")
    if not any(event.get("status") == 200 and event.get("origin_verified") is True
               and _official_url(event.get("url"), "/api/nots/security")
               for event in security_events):
        raise ValueError("no verified official security-list response")
    symbols = capture.get("symbols")
    if not isinstance(symbols, list) or len(symbols) != expected_equity_count:
        raise ValueError(f"expected {expected_equity_count} current equity candidates")
    seen_symbols = set()
    daily = {
        day: {
            "returned_symbol_rows": 0, "missing_symbol_rows": 0,
            "explicit_zero_activity_rows": 0, "positive_activity_rows": 0,
            "trades": Decimal("0"), "volume": Decimal("0"), "turnover": Decimal("0"),
            "missing_symbols": [],
        } for day in expected_dates
    }
    status_counts: Counter[str] = Counter()
    id_matches = 0
    response_count = 0
    for item in symbols:
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol or symbol in seen_symbols:
            raise ValueError("blank or duplicate symbol in official history report")
        seen_symbols.add(symbol)
        status = item.get("status")
        status_counts[str(status)] += 1
        if status != "ROWS_RETURNED_REVIEW_ONLY":
            raise ValueError(f"{symbol}: history capture status is {status!r}")
        if item.get("current_id_match") is not True:
            raise ValueError(f"{symbol}: current security ID does not match crosswalk")
        id_matches += 1
        security_id = str(item.get("current_security_list_id", "")).strip()
        events = item.get("responses")
        if not security_id or not isinstance(events, list) or len(events) != 1:
            raise ValueError(f"{symbol}: expected one pinned history response and a current ID")
        event = events[0]
        response_count += 1
        if event.get("status") != 200 or event.get("origin_verified") is not True:
            raise ValueError(f"{symbol}: response is not verified official HTTP 200")
        if not _official_url(event.get("url"), HISTORY_PATH):
            raise ValueError(f"{symbol}: response URL is not official history endpoint")
        parsed_url = urlparse(event["url"])
        if not parsed_url.path.endswith("/" + security_id):
            raise ValueError(f"{symbol}: response security ID path mismatch")
        query = parse_qs(parsed_url.query)
        if query.get("startDate") != [start_date] or query.get("endDate") != [end_date]:
            raise ValueError(f"{symbol}: response query window mismatch")
        if not event.get("sha256") or event.get("sha256") != item.get("response_sha256"):
            raise ValueError(f"{symbol}: response hash missing or inconsistent")
        rows = item.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"{symbol}: history rows missing")
        by_date = {}
        for row in rows:
            day = row.get("business_date")
            if day in by_date:
                raise ValueError(f"{symbol}: duplicate history row for {day}")
            if day not in daily:
                raise ValueError(f"{symbol}: out-of-range or non-summary history date {day!r}")
            trades = _number(row.get("trades"), f"{symbol} {day} trades")
            volume = _number(row.get("volume"), f"{symbol} {day} volume")
            turnover = _number(row.get("turnover"), f"{symbol} {day} turnover")
            if (trades == 0) != (volume == 0) or (trades == 0) != (turnover == 0):
                raise ValueError(f"{symbol} {day}: zero/nonzero activity metrics are inconsistent")
            by_date[day] = (trades, volume, turnover)
        for day in expected_dates:
            target = daily[day]
            if day not in by_date:
                target["missing_symbol_rows"] += 1
                target["missing_symbols"].append(symbol)
                continue
            trades, volume, turnover = by_date[day]
            target["returned_symbol_rows"] += 1
            if trades == volume == turnover == 0:
                target["explicit_zero_activity_rows"] += 1
            else:
                target["positive_activity_rows"] += 1
            target["trades"] += trades
            target["volume"] += volume
            target["turnover"] += turnover

    market_payload = json.loads(market_body_path.read_text(encoding="utf-8"))
    market_rows = market_payload.get("content") if isinstance(market_payload, dict) else market_payload
    if not isinstance(market_rows, list):
        raise ValueError("official market-summary body has no content list")
    market_by_date = {str(row["businessDate"])[:10]: row for row in market_rows}
    date_reports = {}
    for day in expected_dates:
        item = daily[day]
        market = market_by_date[day]
        totals = {
            "trades": _number(market["totalTransactions"], f"{day} totalTransactions"),
            "volume": _number(market["totalTradedShares"], f"{day} totalTradedShares"),
            "turnover": _number(market["totalTurnover"], f"{day} totalTurnover"),
            "traded_symbols": _number(market["tradedScrips"], f"{day} tradedScrips"),
        }
        equity_totals = {key: item[key] for key in ("trades", "volume", "turnover")}
        if (equity_totals["trades"] > totals["trades"]
                or equity_totals["volume"] > totals["volume"]
                or equity_totals["turnover"] > totals["turnover"]):
            raise ValueError(f"{day}: current-equity history subset exceeds official market totals")
        date_reports[day] = {
            "current_equity_candidate_rows_returned": item["returned_symbol_rows"],
            "current_equity_candidate_rows_missing": item["missing_symbol_rows"],
            "explicit_zero_activity_rows": item["explicit_zero_activity_rows"],
            "positive_activity_rows": item["positive_activity_rows"],
            "missing_symbols": item["missing_symbols"],
            "current_equity_history_totals": {key: str(value) for key, value in equity_totals.items()},
            "official_all_instrument_market_totals": {key: str(value) for key, value in totals.items()},
            "equity_subset_is_not_full_market_universe": True,
        }
    return {
        "schema_version": "1.0",
        "audit_status": "review_only_official_equity_history_window",
        "history_source_id": HISTORY_SOURCE_ID,
        "requested_window": {"start_date": start_date, "end_date": end_date},
        "official_market_summary_evidence": market_identity,
        "official_market_summary_dates_in_window": expected_dates,
        "official_market_summary_date_count": len(expected_dates),
        "equity_candidate_count": len(seen_symbols),
        "current_security_id_crosswalk_matches": id_matches,
        "official_history_response_count": response_count,
        "history_status_counts": dict(sorted(status_counts.items())),
        "date_reports": date_reports,
        "historical_security_identity_verified": False,
        "official_session_calendar_verified": False,
        "full_market_universe_verified": False,
        "per_security_completeness_verified": False,
        "source_independence_verified": False,
        "source_rights_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "current_equity_candidate_history_only_missing_rows_unknown_zero_activity_not_no_trade",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-report", type=Path, required=True)
    parser.add_argument("--market-summary-body", type=Path, required=True)
    parser.add_argument("--market-summary-capture-report", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--expected-equity-count", type=int, default=281)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_history_window(
        args.history_report, args.market_summary_body,
        args.market_summary_capture_report, args.start_date, args.end_date,
        args.expected_equity_count,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "official_market_summary_date_count": report["official_market_summary_date_count"],
        "equity_candidate_count": report["equity_candidate_count"],
        "current_security_id_crosswalk_matches": report["current_security_id_crosswalk_matches"],
        "official_history_response_count": report["official_history_response_count"],
        "date_reports": {
            day: {
                "returned": item["current_equity_candidate_rows_returned"],
                "missing": item["current_equity_candidate_rows_missing"],
                "zero_activity": item["explicit_zero_activity_rows"],
                "positive_activity": item["positive_activity_rows"],
            } for day, item in report["date_reports"].items()
        },
        "historical_security_identity_verified": False,
        "coverage_admission_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

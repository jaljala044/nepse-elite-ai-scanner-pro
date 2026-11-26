"""Capture NEPSE official bulk daily price-volume records for historical business dates."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from capture_nepse_market_summary_history import OFFICIAL_HOSTS

ENDPOINT_PATH = "/api/nots/nepse-data/today-price"
DATE_KEYS = ("businessDate", "business_date", "date")
SYMBOL_KEYS = ("symbol", "stockSymbol", "stock_symbol")
ID_KEYS = ("securityId", "security_id", "id")
VOLUME_KEYS = ("totalTradedQuantity", "total_traded_quantity", "volume")
TURNOVER_KEYS = ("totalTradedValue", "total_traded_value", "turnover")
TRADE_KEYS = ("totalTrades", "total_trades", "totalTransactions")


def _rows_from_payload(payload: object) -> tuple[list, dict]:
    if isinstance(payload, list):
        return payload, {"shape": "list", "total_pages": 1}
    if not isinstance(payload, dict):
        return [], {"shape": type(payload).__name__}
    for key in ("content", "data", "securityDailyTradeStatVos"):
        value = payload.get(key)
        if isinstance(value, list):
            return value, {
                "shape": "object_list",
                "content_key": key,
                "total_pages": payload.get("totalPages", payload.get("total_pages")),
                "total_elements": payload.get("totalElements", payload.get("total_elements")),
            }
        if isinstance(value, dict) and isinstance(value.get("content"), list):
            return value["content"], {
                "shape": "nested_page",
                "content_key": key + ".content",
                "total_pages": value.get("totalPages", value.get("total_pages")),
                "total_elements": value.get("totalElements", value.get("total_elements")),
            }
    return [], {"shape": "unknown_object", "keys": sorted(payload.keys())}


def analyze_daily_payload(payload: object, requested_date: str) -> dict:
    rows, page = _rows_from_payload(payload)
    if not rows:
        return {"status": "UNKNOWN_NO_ROWS_NOT_ZERO_TRADE", "row_count": 0, "reasons": ["no_recognized_rows"], "page": page}
    symbols = set()
    duplicates = []
    invalid = []
    out_of_range = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            invalid.append({"row_index": index, "reason": "row_not_object"})
            continue
        symbol = next((row[key] for key in SYMBOL_KEYS if key in row), None)
        day = next((row[key] for key in DATE_KEYS if key in row), None)
        if not isinstance(symbol, str) or not symbol.strip():
            invalid.append({"row_index": index, "reason": "missing_symbol"})
            continue
        if not isinstance(day, str) or day[:10] != requested_date:
            out_of_range.append({"row_index": index, "date": day})
            continue
        symbol = symbol.strip().upper()
        if symbol in symbols:
            duplicates.append(symbol)
        symbols.add(symbol)
    total_pages = page.get("total_pages")
    total_elements = page.get("total_elements")
    pagination_incomplete = (
        (isinstance(total_pages, int) and total_pages > 1)
        or (isinstance(total_elements, int) and total_elements > len(rows))
    )
    if duplicates or invalid or out_of_range or pagination_incomplete:
        status = "REVIEW_EXCEPTIONS"
    else:
        status = "ROWS_RETURNED_REVIEW_ONLY"
    return {
        "status": status,
        "row_count": len(rows),
        "unique_symbol_count": len(symbols),
        "symbols": sorted(symbols),
        "duplicate_symbols": duplicates,
        "invalid_rows": invalid,
        "out_of_range_rows": out_of_range,
        "pagination_incomplete": pagination_incomplete,
        "page": page,
        "rows": rows,
        "reasons": [],
    }


def capture(dates: list[str], output_dir: Path) -> dict:
    for day in dates:
        date.fromisoformat(day)
    if len(dates) != len(set(dates)):
        raise ValueError("duplicate requested dates")
    output_dir.mkdir(parents=True, exist_ok=True)
    from nepse_client import NepseClient

    client = NepseClient(timeout=90.0)
    base_url = "https://nepalstock.com.np"
    client.base_url = base_url
    client.headers["Host"] = "nepalstock.com.np"
    client.headers["Referer"] = base_url
    current_date = None
    events = []

    def preserve_response(response) -> None:
        parsed = urlparse(str(response.url))
        if parsed.path.rstrip("/") != ENDPOINT_PATH:
            return
        response.read()
        body = response.content
        query = parse_qs(parsed.query)
        events.append({
            "requested_date": current_date,
            "url": str(response.url),
            "status": response.status_code,
            "origin_verified": parsed.scheme == "https" and parsed.hostname in OFFICIAL_HOSTS and parsed.port in (None, 443),
            "query_business_date": query.get("businessDate", [None])[0],
            "response_headers": {key: response.headers.get(key) for key in ("date", "content-type", "server") if response.headers.get(key) is not None},
            "body": body,
            "sha256": hashlib.sha256(body).hexdigest() if body else None,
        })

    client.client.event_hooks["response"].append(preserve_response)
    date_reports = {}
    try:
        for day in dates:
            current_date = day
            error = None
            payload = None
            try:
                payload = client.getPriceVolumeHistory(business_date=day)
            except Exception as exc:
                error = {"type": type(exc).__name__, "message": str(exc)[:300]}
            event = next((item for item in reversed(events) if item["requested_date"] == day), None)
            if event:
                body = event.pop("body")
                (output_dir / f"{day}-response-body.bin").write_bytes(body)
                event["raw_file"] = f"{day}-response-body.bin"
            else:
                body = b""
            origin_ok = bool(event and event["origin_verified"] and event["status"] == 200
                             and event["query_business_date"] == day)
            if error is None and origin_ok:
                analysis = analyze_daily_payload(payload, day)
                (output_dir / f"{day}-parsed-response.json").write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
            else:
                analysis = {"status": "UNKNOWN_CAPTURE_OR_REQUEST", "reasons": [error or "official_origin_or_date_not_verified"]}
            date_reports[day] = {
                "capture_event": event,
                "request_error": error,
                "response_bytes": len(body),
                "response_sha256": hashlib.sha256(body).hexdigest() if body else None,
                "response_origin_verified": origin_ok,
                "analysis": analysis,
            }
    finally:
        client.close()
    report = {
        "schema_version": "1.0",
        "source_id": "NEPSE_OFFICIAL_BULK_DAILY_PRICE_VOLUME",
        "endpoint_path": ENDPOINT_PATH,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "date_reports": date_reports,
        "per_security_completeness_verified": False,
        "historical_security_identity_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "official_daily_per_security_response_capture_review_only_no_missing_row_to_no_trade_inference",
    }
    (output_dir / "capture-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{item['response_sha256']}  {day}-response-body.bin\n"
                for day, item in date_reports.items() if item.get("response_sha256")),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dates", nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    report = capture(args.dates, args.output_dir)
    print(json.dumps({
        "date_statuses": {day: item["analysis"].get("status") for day, item in report["date_reports"].items()},
        "row_counts": {day: item["analysis"].get("row_count") for day, item in report["date_reports"].items()},
        "per_security_completeness_verified": False,
        "coverage_admission_allowed": False,
    }, indent=2))
    return 0 if all(item["response_origin_verified"] for item in report["date_reports"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Capture official NEPSE per-security history for a bounded date window.

A missing symbol/date row is UNKNOWN, never proof of zero trading. The current
security-list ID is recorded as a snapshot mapping, not historical identity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

OFFICIAL_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}
HISTORY_PREFIX = "/api/nots/market/history/security/"
HISTORY_FIELDS = {
    "date": ("businessDate", "business_date", "date"),
    "trades": ("totalTrades", "total_trades", "totalTransactions"),
    "volume": ("totalTradedQuantity", "total_traded_quantity", "volume"),
    "turnover": ("totalTradedValue", "total_traded_value", "turnover"),
}


def load_crosswalk(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "symbol" not in rows[0] or "security_id" not in rows[0]:
        raise ValueError("crosswalk must contain symbol and security_id")
    symbols = [row["symbol"].strip().upper() for row in rows]
    if any(not symbol for symbol in symbols) or len(symbols) != len(set(symbols)):
        raise ValueError("crosswalk contains blank or duplicate symbols")
    return rows


def extract_history_payload(payload: object, start_date: str, end_date: str) -> dict:
    if isinstance(payload, dict):
        rows = payload.get("content")
        total_pages = payload.get("totalPages", payload.get("total_pages"))
        total_elements = payload.get("totalElements", payload.get("total_elements"))
    elif isinstance(payload, list):
        rows, total_pages, total_elements = payload, 1, len(payload)
    else:
        return {"status": "UNKNOWN_SCHEMA", "rows": [], "reasons": ["unexpected_payload_type"]}
    if not isinstance(rows, list):
        return {"status": "UNKNOWN_SCHEMA", "rows": [], "reasons": ["missing_content_array"]}
    if total_pages is not None and (not isinstance(total_pages, int) or total_pages < 1):
        return {"status": "UNKNOWN_SCHEMA", "rows": [], "reasons": ["invalid_total_pages"]}
    if total_pages not in (None, 1):
        return {"status": "PAGINATION_INCOMPLETE", "rows": [], "reasons": ["more_than_one_page_required"], "total_pages": total_pages}
    accepted = []
    seen_dates = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            return {"status": "UNKNOWN_SCHEMA", "rows": [], "reasons": [f"row_{index}_not_object"]}
        date_value = next((row[key] for key in HISTORY_FIELDS["date"] if key in row), None)
        if not isinstance(date_value, str):
            return {"status": "UNKNOWN_SCHEMA", "rows": [], "reasons": [f"row_{index}_missing_date"]}
        day = date_value[:10]
        try:
            date.fromisoformat(day)
        except ValueError:
            return {"status": "UNKNOWN_SCHEMA", "rows": [], "reasons": [f"row_{index}_invalid_date"]}
        if not start_date <= day <= end_date:
            return {"status": "OUT_OF_RANGE_ROW", "rows": [], "reasons": [f"row_{index}_outside_requested_range"]}
        if day in seen_dates:
            return {"status": "DUPLICATE_DATE_ROW", "rows": [], "reasons": [f"duplicate_date_{day}"]}
        seen_dates.add(day)
        normalized = {"business_date": day}
        for name in ("trades", "volume", "turnover"):
            value = next((row[key] for key in HISTORY_FIELDS[name] if key in row), None)
            normalized[name] = value
        normalized["raw"] = row
        accepted.append(normalized)
    if total_elements is not None and isinstance(total_elements, int) and total_elements > len(accepted):
        return {"status": "PAGINATION_INCOMPLETE", "rows": accepted, "reasons": ["total_elements_exceeds_returned_rows"], "total_elements": total_elements}
    if not accepted:
        return {"status": "UNKNOWN_NO_ROWS_NOT_ZERO_TRADE", "rows": [], "reasons": ["no_history_rows_returned"]}
    return {"status": "ROWS_RETURNED_REVIEW_ONLY", "rows": accepted, "reasons": [], "total_pages": total_pages, "total_elements": total_elements}


def capture(crosswalk_path: Path, output_dir: Path, start_date: str, end_date: str, pause_seconds: float = 0.1) -> dict:
    date.fromisoformat(start_date)
    date.fromisoformat(end_date)
    if start_date > end_date:
        raise ValueError("start_date must not exceed end_date")
    if pause_seconds < 0:
        raise ValueError("pause_seconds must be nonnegative")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_crosswalk(crosswalk_path)
    from nepse_client import NepseClient

    client = NepseClient(timeout=90.0)
    base_url = "https://nepalstock.com.np"
    client.base_url = base_url
    client.headers["Host"] = "nepalstock.com.np"
    client.headers["Referer"] = base_url
    response_events = []
    current_symbol = "__SECURITY_LIST__"

    def preserve_response(response) -> None:
        parsed = urlparse(str(response.url))
        if not parsed.path.startswith(HISTORY_PREFIX) and parsed.path.rstrip("/") != "/api/nots/security":
            return
        response.read()
        body = response.content
        response_events.append({
            "symbol": current_symbol,
            "url": str(response.url),
            "status": response.status_code,
            "origin_verified": parsed.scheme == "https" and parsed.hostname in OFFICIAL_HOSTS and parsed.port in (None, 443),
            "body": body,
            "sha256": hashlib.sha256(body).hexdigest() if body else None,
            "headers": {key: response.headers.get(key) for key in ("date", "content-type", "server") if response.headers.get(key) is not None},
        })

    client.client.event_hooks["response"].append(preserve_response)
    symbol_reports = []
    try:
        try:
            security_map = client.getSecurityIDKeyMap(force_update=True)
            security_map_error = None
        except Exception as exc:
            security_map = {}
            security_map_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
        for index, row in enumerate(rows, start=1):
            symbol = row["symbol"].strip().upper()
            expected_id = str(row.get("security_id", "")).strip()
            observed_id = security_map.get(symbol)
            item = {
                "symbol": symbol,
                "crosswalk_security_id": expected_id or None,
                "current_security_list_id": str(observed_id) if observed_id is not None else None,
                "current_id_match": observed_id is not None and expected_id == str(observed_id),
                "historical_security_identity_verified": False,
                "status": None,
                "reasons": [],
                "responses": [],
            }
            if observed_id is None:
                item["status"] = "SECURITY_ID_UNRESOLVED"
                item["reasons"] = ["symbol_absent_from_current_official_security_list"]
                symbol_reports.append(item)
                continue
            current_symbol = symbol
            event_start = len(response_events)
            try:
                payload = client.getCompanyPriceVolumeHistory(symbol, start_date=start_date, end_date=end_date)
                relevant_events = response_events[event_start:]
                for event_index, event in enumerate(relevant_events, start=1):
                    body = event.pop("body")
                    folder = output_dir / "symbols" / symbol
                    folder.mkdir(parents=True, exist_ok=True)
                    filename = f"response-{event_index:02d}.bin"
                    (folder / filename).write_bytes(body)
                    event["raw_file"] = str(Path("symbols") / symbol / filename)
                    item["responses"].append(event)
                selected = next((event for event in reversed(relevant_events)
                                 if event["status"] == 200 and event["origin_verified"]), None)
                if selected is None:
                    item["status"] = "REQUEST_ERROR_OR_UNVERIFIED_ORIGIN"
                    item["reasons"] = ["no_verified_http_200_history_response"]
                else:
                    parsed = payload
                    parsed_result = extract_history_payload(parsed, start_date, end_date)
                    item["status"] = parsed_result["status"]
                    item["reasons"] = parsed_result.get("reasons", [])
                    item["rows"] = parsed_result.get("rows", [])
                    item["pagination"] = {
                        "total_pages": parsed_result.get("total_pages"),
                        "total_elements": parsed_result.get("total_elements"),
                    }
                    item["response_sha256"] = selected["sha256"]
                    item["response_url"] = selected["url"]
                    if selected["url"].find(f"{HISTORY_PREFIX}{observed_id}") < 0:
                        item["status"] = "RESPONSE_ID_PATH_MISMATCH"
                        item["reasons"] = ["response_path_does_not_match_current_security_id"]
            except Exception as exc:
                item["status"] = "REQUEST_ERROR"
                item["reasons"] = [{"type": type(exc).__name__, "message": str(exc)[:300]}]
                for event_index, event in enumerate(response_events[event_start:], start=1):
                    body = event.pop("body")
                    folder = output_dir / "symbols" / symbol
                    folder.mkdir(parents=True, exist_ok=True)
                    filename = f"response-{event_index:02d}.bin"
                    (folder / filename).write_bytes(body)
                    event["raw_file"] = str(Path("symbols") / symbol / filename)
                    item["responses"].append(event)
            symbol_reports.append(item)
            if pause_seconds:
                time.sleep(pause_seconds)
    finally:
        client.close()

    for event in response_events:
        event.pop("body", None)
    status_counts = {}
    for item in symbol_reports:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    report = {
        "schema_version": "1.0",
        "source_id": "NEPSE_OFFICIAL_PER_SECURITY_PRICE_VOLUME_HISTORY",
        "endpoint_path": HISTORY_PREFIX + "{security_id}",
        "base_url": base_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "crosswalk_path": str(crosswalk_path),
        "crosswalk_row_count": len(rows),
        "security_list_error": security_map_error,
        "status_counts": status_counts,
        "response_event_count": len(response_events),
        "symbols": symbol_reports,
        "historical_security_identity_verified": False,
        "per_security_completeness_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "official_per_security_history_capture_review_only_missing_rows_are_unknown_not_no_trade",
    }
    (output_dir / "capture-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{item['response_sha256']}  {item['raw_file']}\n"
                for symbol in symbol_reports for item in symbol["responses"] if item.get("response_sha256")),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--pause-seconds", type=float, default=0.1)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    report = capture(args.crosswalk, args.output_dir, args.start_date, args.end_date, args.pause_seconds)
    print(json.dumps({
        "crosswalk_row_count": report["crosswalk_row_count"],
        "status_counts": report["status_counts"],
        "response_event_count": report["response_event_count"],
        "per_security_completeness_verified": False,
        "coverage_admission_allowed": False,
    }, indent=2))
    return 0 if report["status_counts"] and not report["security_list_error"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

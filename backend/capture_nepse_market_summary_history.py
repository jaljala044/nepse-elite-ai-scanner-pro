#!/usr/bin/env python3
"""Capture NEPSE's official market-summary-history API as immutable raw evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

SOURCE_ID = "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY"
ENDPOINT_PATH = "/api/nots/market-summary-history"
SOURCE_URL = "https://nepalstock.com.np" + ENDPOINT_PATH  # fallback host: https://newweb.nepalstock.com
DATE_FIELDS = ("businessDate", "business_date", "businessdate", "date")


def _as_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def load_candidate_dates(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["date"].strip()
            for row in csv.DictReader(handle)
            if row.get("date", "").strip()
        }


SUMMARY_METRIC_FIELDS = {
    "total_turnover": ("totalTurnover", "total_turnover"),
    "total_traded_shares": ("totalTradedShares", "total_traded_shares"),
    "total_transactions": ("totalTransactions", "total_transactions", "totalTransaction"),
    "traded_scrips": ("tradedScrips", "traded_scrips"),
}


def _positive_decimal(row: dict, aliases: tuple[str, ...]) -> Decimal | None:
    value = next((row[key] for key in aliases if key in row), None)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number > 0 else None


def analyze_payload(payload: object, candidate_dates: set[str] | None = None) -> dict:
    if not isinstance(payload, list):
        return {
            "payload_type": type(payload).__name__,
            "record_count": None,
            "date_field": None,
            "date_record_count": 0,
            "unique_date_count": 0,
            "invalid_date_row_count": 0,
            "date_comparison": None,
            "canonical_calendar_promotion_allowed": False,
            "activity_validated_record_count": 0,
            "activity_confirmed_date_count": 0,
            "activity_confirmed_dates": [],
            "activity_unverified_rows": [],
            "activity_duplicate_dates": [],
        }

    date_field = None
    parsed_values: list[str | None] = []
    for field in DATE_FIELDS:
        values = [_as_date(row.get(field)) if isinstance(row, dict) else None for row in payload]
        if any(value is not None for value in values):
            date_field = field
            parsed_values = values
            break

    if date_field is None:
        return {
            "payload_type": "list",
            "record_count": len(payload),
            "date_field": None,
            "date_record_count": 0,
            "unique_date_count": 0,
            "invalid_date_row_count": len(payload),
            "date_comparison": None,
            "canonical_calendar_promotion_allowed": False,
        }

    dates = [value for value in parsed_values if value is not None]
    counts = Counter(dates)
    unique_dates = set(dates)
    activity_by_date: dict[str, list[tuple[Decimal, ...]]] = {}
    activity_unverified_rows: list[dict] = []
    for index, row in enumerate(payload):
        day = parsed_values[index]
        if day is None or not isinstance(row, dict):
            activity_unverified_rows.append({"row_index": index, "date": day, "reason": "invalid_date_or_row_shape"})
            continue
        metrics = tuple(_positive_decimal(row, aliases) for aliases in SUMMARY_METRIC_FIELDS.values())
        if any(value is None for value in metrics):
            missing = [name for (name, _), value in zip(SUMMARY_METRIC_FIELDS.items(), metrics) if value is None]
            activity_unverified_rows.append({"row_index": index, "date": day, "reason": "missing_invalid_or_nonpositive_activity_metrics", "fields": missing})
            continue
        activity_by_date.setdefault(day, []).append(tuple(value for value in metrics if value is not None))
    activity_duplicate_dates = sorted(day for day, rows_for_day in activity_by_date.items() if counts[day] > 1)
    activity_confirmed_dates = sorted(
        day for day, rows_for_day in activity_by_date.items()
        if counts[day] == 1 and len(rows_for_day) == 1
    )
    comparison = None
    if candidate_dates is not None:
        comparison = {
            "candidate_date_count": len(candidate_dates),
            "primary_summary_unique_date_count": len(unique_dates),
            "candidate_dates_with_primary_summary": len(candidate_dates & unique_dates),
            "candidate_dates_without_primary_summary": sorted(candidate_dates - unique_dates),
            "candidate_dates_with_validated_activity": sorted(candidate_dates & set(activity_confirmed_dates)),
            "candidate_dates_without_validated_activity": sorted(candidate_dates - set(activity_confirmed_dates)),
            "primary_summary_dates_outside_candidate_set": sorted(unique_dates - candidate_dates),
        }

    return {
        "payload_type": "list",
        "record_count": len(payload),
        "date_field": date_field,
        "date_record_count": len(dates),
        "unique_date_count": len(unique_dates),
        "duplicate_date_rows": sum(count - 1 for count in counts.values() if count > 1),
        "duplicate_dates": [
            {"date": day, "record_count": count}
            for day, count in sorted(counts.items()) if count > 1
        ],
        "invalid_date_row_count": len(payload) - len(dates),
        "activity_metric_fields": {name: list(aliases) for name, aliases in SUMMARY_METRIC_FIELDS.items()},
        "activity_validated_record_count": sum(len(rows_for_day) for rows_for_day in activity_by_date.values()),
        "activity_confirmed_date_count": len(activity_confirmed_dates),
        "activity_confirmed_dates": activity_confirmed_dates,
        "activity_unverified_rows": activity_unverified_rows,
        "activity_duplicate_dates": activity_duplicate_dates,
        "first_date": min(unique_dates) if unique_dates else None,
        "last_date": max(unique_dates) if unique_dates else None,
        "date_comparison": comparison,
        "canonical_calendar_promotion_allowed": False,
    }


def capture(output_dir: Path, candidate_csv: Path | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    attempts: list[dict] = []
    request_errors: list[dict] = []
    successful_payload = None
    successful_url = None
    successful_headers: dict = {}
    successful_body: bytes | None = None

    from nepse_client import NepseClient

    base_urls = ("https://nepalstock.com.np", "https://newweb.nepalstock.com")
    for attempt_number, base_url in enumerate(base_urls, start=1):
        captured: dict = {}
        request_error = None
        client = NepseClient(timeout=90.0)
        client.base_url = base_url
        client.headers["Host"] = base_url.removeprefix("https://")
        client.headers["Referer"] = base_url

        def preserve_response(response) -> None:
            if urlparse(str(response.url)).path != ENDPOINT_PATH:
                return
            response.read()
            captured["body"] = response.content
            captured["status"] = response.status_code
            captured["url"] = str(response.url)
            captured["headers"] = {
                key: response.headers.get(key)
                for key in ("date", "content-type", "content-length", "server")
                if response.headers.get(key) is not None
            }

        client.client.event_hooks["response"].append(preserve_response)
        try:
            client.requestGETAPI(ENDPOINT_PATH)
        except Exception as exc:
            request_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
        finally:
            client.close()

        body = captured.get("body", b"")
        attempt = {
            "attempt_number": attempt_number,
            "base_url": base_url,
            "source_url": captured.get("url", base_url + ENDPOINT_PATH),
            "http_status": captured.get("status"),
            "response_headers": captured.get("headers", {}),
            "response_bytes": len(body),
            "response_sha256": hashlib.sha256(body).hexdigest() if body else None,
            "response_preserved": bool(body),
            "request_error": request_error,
        }
        attempts.append(attempt)
        if request_error is not None:
            request_errors.append({"attempt_number": attempt_number, **request_error})
        if body:
            prefix = f"attempt-{attempt_number:02d}"
            (output_dir / f"{prefix}-response-body.bin").write_bytes(body)
            (output_dir / f"{prefix}-response-headers.json").write_text(
                json.dumps(captured.get("headers", {}), indent=2) + "\n",
                encoding="utf-8",
            )
            (output_dir / f"{prefix}-SHA256SUMS").write_text(
                f"{attempt['response_sha256']}  {prefix}-response-body.bin\n",
                encoding="utf-8",
            )

        if captured.get("status") == 200 and body:
            successful_payload = None
            try:
                successful_payload = json.loads(body)
            except Exception:
                pass
            successful_url = captured.get("url", base_url + ENDPOINT_PATH)
            successful_headers = captured.get("headers", {})
            successful_body = body
            break

    report = {
        "source_id": SOURCE_ID,
        "source_url": successful_url or attempts[-1]["source_url"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "attempts": attempts,
        "request_errors": request_errors,
        "selected_attempt_number": next(
            (item["attempt_number"] for item in attempts if item["http_status"] == 200 and item["response_preserved"]),
            None,
        ),
        "http_status": next(
            (item["http_status"] for item in attempts if item["http_status"] == 200 and item["response_preserved"]),
            attempts[-1]["http_status"],
        ),
        "response_headers": successful_headers,
        "response_bytes": len(successful_body or b""),
        "response_sha256": hashlib.sha256(successful_body).hexdigest() if successful_body else None,
        "response_preserved": bool(successful_body),
        "calendar_claims_promoted": False,
        "canonical_calendar_promotion_allowed": False,
        "policy": "raw primary-source capture only; review schema and date scope before any calendar promotion",
    }

    if successful_body is not None:
        (output_dir / "response-body.bin").write_bytes(successful_body)
        (output_dir / "source-url.txt").write_text(successful_url + "\n", encoding="utf-8")
        (output_dir / "response-headers.json").write_text(
            json.dumps(successful_headers, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "SHA256SUMS").write_text(
            f"{report['response_sha256']}  response-body.bin\n",
            encoding="utf-8",
        )
        if successful_payload is not None:
            (output_dir / "parsed-response.json").write_text(
                json.dumps(successful_payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["payload_analysis"] = analyze_payload(
                successful_payload, load_candidate_dates(candidate_csv)
            )
            (output_dir / "payload-analysis.json").write_text(
                json.dumps(report["payload_analysis"], indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            report["json_parse_error"] = "JSONDecodeError"

    (output_dir / "capture-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate-csv", type=Path, default=None)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    report = capture(args.output_dir, args.candidate_csv)
    print(json.dumps({
        "http_status": report["http_status"],
        "response_bytes": report["response_bytes"],
        "response_sha256": report["response_sha256"],
        "response_preserved": report["response_preserved"],
        "request_errors": report["request_errors"],
        "payload_analysis": report.get("payload_analysis"),
        "calendar_claims_promoted": False,
    }, indent=2))
    return 0 if report["http_status"] == 200 and report["response_preserved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

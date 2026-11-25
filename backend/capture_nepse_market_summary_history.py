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
from pathlib import Path
from urllib.parse import urlparse

SOURCE_ID = "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY"
ENDPOINT_PATH = "/api/nots/market-summary-history"
SOURCE_URL = "https://nepalstock.com.np" + ENDPOINT_PATH
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
    comparison = None
    if candidate_dates is not None:
        comparison = {
            "candidate_date_count": len(candidate_dates),
            "primary_summary_unique_date_count": len(unique_dates),
            "candidate_dates_with_primary_summary": len(candidate_dates & unique_dates),
            "candidate_dates_without_primary_summary": sorted(candidate_dates - unique_dates),
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
        "first_date": min(unique_dates) if unique_dates else None,
        "last_date": max(unique_dates) if unique_dates else None,
        "date_comparison": comparison,
        "canonical_calendar_promotion_allowed": False,
    }


def capture(output_dir: Path, candidate_csv: Path | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    captured: dict = {}
    request_error = None

    from nepse_client import NepseClient

    client = NepseClient(timeout=90.0)

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

    report = {
        "source_id": SOURCE_ID,
        "source_url": captured.get("url", SOURCE_URL),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "http_status": captured.get("status"),
        "response_headers": captured.get("headers", {}),
        "response_bytes": len(captured.get("body", b"")),
        "response_sha256": None,
        "response_preserved": "body" in captured,
        "request_error": request_error,
        "calendar_claims_promoted": False,
        "canonical_calendar_promotion_allowed": False,
        "policy": "raw_primary_source_capture_only; review schema and date scope before any calendar promotion",
    }

    if "body" in captured:
        body = captured["body"]
        report["response_sha256"] = hashlib.sha256(body).hexdigest()
        (output_dir / "response-body.bin").write_bytes(body)
        try:
            payload = json.loads(body)
            (output_dir / "parsed-response.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["payload_analysis"] = analyze_payload(
                payload, load_candidate_dates(candidate_csv)
            )
        except Exception as exc:
            report["json_parse_error"] = type(exc).__name__
        (output_dir / "response-headers.json").write_text(
            json.dumps(captured.get("headers", {}), indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "source-url.txt").write_text(captured["url"] + "\n", encoding="utf-8")
        (output_dir / "SHA256SUMS").write_text(
            f"{report['response_sha256']}  response-body.bin\n",
            encoding="utf-8",
        )
        if "payload_analysis" in report:
            (output_dir / "payload-analysis.json").write_text(
                json.dumps(report["payload_analysis"], indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

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
        "request_error": report["request_error"],
        "payload_analysis": report.get("payload_analysis"),
        "calendar_claims_promoted": False,
    }, indent=2))
    return 0 if report["http_status"] == 200 and report["response_preserved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Capture NEPSE's official security-classification API as immutable raw evidence.

The endpoint is paginated (20 rows per page). Raw response bytes are preserved
per page before parsing; authentication tokens are never written to disk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SOURCE_ID = "NEPSE_OFFICIAL_SECURITY_CLASSIFICATION"
ENDPOINT_PATH = "/api/nots/security/classification"
SOURCE_URL = "https://nepalstock.com.np" + ENDPOINT_PATH
PAGE_SIZE = 20
OFFICIAL_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}


def capture(output_dir: Path, max_pages: int = 40) -> dict:
    from nepse_client import NepseClient

    output_dir.mkdir(parents=True, exist_ok=True)
    client = NepseClient(timeout=60.0)
    captured_pages: list[dict] = []

    def save_response(response) -> None:
        parsed = urlparse(str(response.url))
        if parsed.path.rstrip("/") != ENDPOINT_PATH:
            return
        response.read()
        captured_pages.append({
            "url": str(response.url),
            "status": response.status_code,
            "headers": {
                key: response.headers.get(key)
                for key in ("date", "content-type", "content-length", "server")
                if response.headers.get(key) is not None
            },
            "body": response.content,
            "origin_verified": (
                parsed.scheme == "https"
                and parsed.hostname in OFFICIAL_HOSTS
                and parsed.port in (None, 443)
            ),
        })

    client.client.event_hooks["response"].append(save_response)
    request_errors: list[dict] = []
    try:
        page = 0
        total_pages = None
        while page < max_pages:
            before = len(captured_pages)
            try:
                payload = client.requestGETAPI(f"{ENDPOINT_PATH}?page={page}")
            except Exception as exc:
                request_errors.append({
                    "page": page,
                    "type": type(exc).__name__,
                    "message": str(exc)[:300],
                })
                break
            if isinstance(payload, dict):
                tp = payload.get("totalPages")
                if isinstance(tp, int):
                    total_pages = tp
            content = payload.get("content", []) if isinstance(payload, dict) else payload
            if not content:
                break
            page += 1
            if total_pages is not None and page >= total_pages:
                break
            if len(captured_pages) == before:
                request_errors.append({"page": page - 1, "type": "NoResponseCaptured"})
                break
    finally:
        client.close()

    page_reports = []
    all_rows: list[dict] = []
    for index, item in enumerate(captured_pages):
        body = item["body"]
        sha = hashlib.sha256(body).hexdigest() if body else None
        filename = f"page-{index:03d}-response-body.bin"
        (output_dir / filename).write_bytes(body)
        parsed_payload = None
        try:
            parsed_payload = json.loads(body)
        except Exception:
            pass
        rows = []
        if isinstance(parsed_payload, dict):
            rows = parsed_payload.get("content", [])
        elif isinstance(parsed_payload, list):
            rows = parsed_payload
        all_rows.extend(row for row in rows if isinstance(row, dict))
        page_reports.append({
            "page_index": index,
            "request_url": item["url"],
            "http_status": item["status"],
            "response_bytes": len(body),
            "response_sha256": sha,
            "response_headers": item["headers"],
            "origin_verified": item["origin_verified"],
            "row_count": len(rows),
            "filename": filename,
        })

    symbols = [row.get("symbol") for row in all_rows]
    report = {
        "source_id": SOURCE_ID,
        "endpoint_path": ENDPOINT_PATH,
        "source_url": SOURCE_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "page_reports": page_reports,
        "pages_captured": len(page_reports),
        "total_pages_reported": total_pages,
        "row_count": len(all_rows),
        "unique_symbol_count": len({s for s in symbols if s}),
        "duplicate_symbol_count": len(symbols) - len({s for s in symbols if s}),
        "fields_of_interest": ["id", "symbol", "listingDate", "tradingStartDate",
                               "activeStatus", "isin", "instrumentType"],
        "request_errors": request_errors,
        "calendar_claims_promoted": False,
        "canonical_promotion_allowed": False,
        "policy": "raw primary-source capture only; review schema and semantics before any lifecycle promotion",
    }
    (output_dir / "capture-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{p['response_sha256']}  {p['filename']}\n"
                for p in page_reports if p["response_sha256"]),
        encoding="utf-8",
    )
    (output_dir / "parsed-classification.json").write_text(
        json.dumps(all_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-pages", type=int, default=40)
    args = parser.parse_args()
    report = capture(args.output_dir, args.max_pages)
    print(json.dumps({k: report[k] for k in (
        "source_id", "retrieved_at_utc", "pages_captured", "total_pages_reported",
        "row_count", "unique_symbol_count", "duplicate_symbol_count", "request_errors")},
        indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

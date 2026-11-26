#!/usr/bin/env python3
"""Import an archived official NEPSE market-summary response into bronze evidence.

Rows are always stored review_required/provisional. This command never promotes
source trust, exchange sessions, market-health inputs, or trading signals.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse
from app.evidence_store import persist_evidence_batch

SOURCE_ID = "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY"
OFFICIAL_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}
DATE_FIELDS = ("businessDate", "business_date", "businessdate", "date")

def _timestamp(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("capture report must contain retrieved_at_utc")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("retrieved_at_utc must be timezone-aware")
    return parsed.isoformat().replace("+00:00", "Z")

def _session_date(row):
    for field in DATE_FIELDS:
        value = row.get(field)
        if isinstance(value, str) and len(value) >= 10:
            candidate = value[:10]
            try:
                if date.fromisoformat(candidate).isoformat() == candidate:
                    return candidate
            except ValueError:
                pass
    return None

def import_capture(output_dir: Path, *, storage_root: Path, database_path: Path):
    report = json.loads((output_dir / "capture-report.json").read_text(encoding="utf-8"))
    payload = (output_dir / "response-body.bin").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if report.get("source_id") != SOURCE_ID:
        raise ValueError("capture report source_id is not the official NEPSE market-summary source")
    if report.get("http_status") != 200 or not report.get("response_preserved"):
        raise ValueError("only a preserved HTTP 200 capture can be imported")
    parsed = urlparse(report.get("source_url") or "")
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS or parsed.port not in (None, 443):
        raise ValueError("capture response URL is not an approved official NEPSE HTTPS host")
    if parsed.path.rstrip("/") != "/api/nots/market-summary-history":
        raise ValueError("capture response URL is not the expected market-summary-history endpoint")
    if report.get("response_sha256") != digest:
        raise ValueError("capture report SHA-256 does not match exact response bytes")
    if report.get("response_bytes") != len(payload):
        raise ValueError("capture report byte length does not match exact response bytes")
    received_at = _timestamp(report.get("retrieved_at_utc"))
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("official response must be a UTF-8 JSON payload") from exc
    if not isinstance(decoded, list):
        raise ValueError("official market-summary response must be a JSON array")
    records = []
    for index, row in enumerate(decoded, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"response row {index} must be an object")
        records.append({
            "source_row_number": index, "record_type": "market_summary",
            "session_date": _session_date(row), "available_at": received_at,
            "raw_source_record": row,
        })
    # The capture report lacks request-start time. Use receipt time for both
    # manifest bounds rather than inventing or backdating availability.
    manifest = {
        "schema_version": 1, "source_id": SOURCE_ID,
        "source_url": report["source_url"], "request_method": "GET",
        "request_metadata": {
            "capture_report": "capture-report.json",
            "selected_attempt_number": report.get("selected_attempt_number"),
            "response_headers": report.get("response_headers") or {},
            "timestamp_semantics": "retrieved_at_utc used conservatively for request and receipt bounds",
        },
        "requested_at_utc": received_at, "received_at_utc": received_at,
        "claimed_session_date": None, "verified_session_date": None,
        "session_status": "unverified", "session_evidence_ref": None,
        "http_status": 200,
        "content_type": (report.get("response_headers") or {}).get("content-type"),
        "fetch_id": f"nepse-market-summary-{digest[:24]}",
        "parser_version": "nepse-market-summary-bronze-v1",
        "rights_status": "unknown", "payload_bytes": len(payload),
        "payload_sha256": digest,
    }
    return persist_evidence_batch(payload, manifest, records,
        storage_root=storage_root, database_path=database_path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(import_capture(args.capture_dir, storage_root=args.storage_root,
        database_path=args.database), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

"""Import captured official NEPSE market-summary bytes into bronze evidence storage.

Imported rows are always review_required/provisional. This utility does not
promote records, infer missing sessions, or manufacture OHLCV.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from app.evidence_store import persist_evidence_batch
from app.raw_capture import build_capture_manifest

SOURCE_ID = "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY"
OFFICIAL_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}
DATE_FIELDS = ("businessDate", "business_date", "businessdate", "date")
METRICS = {
    "total_turnover": ("totalTurnover", "total_turnover"),
    "total_traded_shares": ("totalTradedShares", "total_traded_shares"),
    "total_transactions": ("totalTransactions", "total_transactions", "totalTransaction"),
    "traded_scrips": ("tradedScrips", "traded_scrips"),
}

def _positive(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return str(number) if number.is_finite() and number > 0 else None

def import_capture(report_path: Path, *, storage_root: Path, database_path: Path | None = None) -> dict:
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("source_id") != SOURCE_ID:
        raise ValueError("capture report source_id is not the official market-summary source")
    if report.get("http_status") != 200 or report.get("response_preserved") is not True or report.get("response_origin_verified") is not True:
        raise ValueError("capture report does not prove a preserved HTTP 200 response from an official origin")
    source_url = report.get("source_url")
    parsed_url = urlparse(str(source_url or ""))
    if parsed_url.scheme != "https" or parsed_url.hostname not in OFFICIAL_HOSTS or parsed_url.path.rstrip("/") != "/api/nots/market-summary-history" or parsed_url.port not in (None, 443):
        raise ValueError("capture URL is not the expected official NEPSE market-summary endpoint")
    retrieved_at = report.get("retrieved_at_utc")
    try:
        received = datetime.fromisoformat(str(retrieved_at).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("capture retrieval timestamp is invalid") from exc
    if received.tzinfo is None or received.utcoffset() is None:
        raise ValueError("capture retrieval timestamp must be timezone-aware")
    raw_path = report_path.parent / "response-body.bin"
    payload = raw_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != report.get("response_sha256") or len(payload) != report.get("response_bytes"):
        raise ValueError("captured response bytes do not match report digest or length")
    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, list):
        raise ValueError("official market-summary response must be a JSON array")

    dates = []
    candidates = []
    rejected = []
    for index, row in enumerate(decoded):
        if not isinstance(row, dict):
            rejected.append({"source_row_number": index + 1, "reason": "row_not_object"})
            continue
        raw_day = next((row.get(key) for key in DATE_FIELDS if row.get(key) is not None), None)
        if not isinstance(raw_day, str):
            rejected.append({"source_row_number": index + 1, "reason": "missing_session_date"})
            continue
        try:
            day = datetime.fromisoformat(raw_day[:10]).date().isoformat()
        except ValueError:
            rejected.append({"source_row_number": index + 1, "reason": "invalid_session_date"})
            continue
        values = {name: _positive(next((row.get(key) for key in aliases if row.get(key) is not None), None))
                  for name, aliases in METRICS.items()}
        if any(value is None for value in values.values()):
            rejected.append({"source_row_number": index + 1, "session_date": day, "reason": "missing_or_invalid_activity_metric"})
            continue
        dates.append(day)
        candidates.append({"source_row_number": index + 1, "record_type": "market_summary",
                           "session_date": day, **values})
    counts = Counter(dates)
    duplicate_dates = {day for day, count in counts.items() if count > 1}
    records = [row for row in candidates if row["session_date"] not in duplicate_dates]
    rejected.extend({"source_row_number": row["source_row_number"], "session_date": row["session_date"],
                     "reason": "duplicate_session_summary"} for row in candidates if row["session_date"] in duplicate_dates)

    fetch_id = "nepse-market-summary-" + digest[:24]
    timestamp = received.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = build_capture_manifest(
        payload, source_id=SOURCE_ID, source_url=source_url,
        request_method="GET", request_metadata={"capture_report": report_path.name, "capture_digest": digest},
        requested_at=timestamp, received_at=timestamp,
        claimed_session_date=max((row["session_date"] for row in records), default=None),
        fetch_id=fetch_id, parser_version="official-market-summary-import-v1",
        rights_status="unknown",
    )
    stored = persist_evidence_batch(
        payload, manifest, records, storage_root=storage_root,
        database_path=database_path,
    )
    return {
        "status": "stored_review_required",
        "source_id": SOURCE_ID,
        "fetch_id": fetch_id,
        "raw_payload_sha256": digest,
        "input_rows": len(decoded),
        "normalized_rows": len(records),
        "rejected_rows": len(rejected),
        "rejections": rejected,
        "row_conservation_passed": len(decoded) == len(records) + len(rejected),
        "production_eligible": False,
        "canonical_promotion_allowed": False,
        "evidence_store": stored,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-report", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=None)
    args = parser.parse_args()
    result = import_capture(args.capture_report, storage_root=args.storage_root, database_path=args.database)
    print(json.dumps({key: result[key] for key in ("status","input_rows","normalized_rows","rejected_rows","row_conservation_passed","production_eligible","canonical_promotion_allowed")}, indent=2))
    return 0 if result["row_conservation_passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())

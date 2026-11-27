"""Normalize captured CSV OHLCV pages into provenance-preserving pilot rows.

No source access, column guessing, row repair or silent row dropping is performed.
The caller must supply the explicit schema mapping for the approved source.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from datetime import date, datetime
from typing import Mapping

from app.historical_pilot_capture import manifest_sha256

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROW_HASH_FIELDS = (
    "symbol", "session_date", "open", "high", "low", "close", "volume",
    "source_id", "publisher_id", "capture_id", "payload_id", "page_number",
    "source_row_number", "raw_sha256", "capture_manifest_sha256",
)


def calculate_pilot_row_sha256(row: Mapping[str, object]) -> str:
    """Fingerprint normalized values and every locator needed to recover the raw row."""
    payload = {
        "symbol": str(row["symbol"]),
        "session_date": str(row["session_date"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": int(row["volume"]),
        "source_id": str(row["source_id"]),
        "publisher_id": str(row["publisher_id"]),
        "capture_id": str(row["capture_id"]),
        "payload_id": str(row["payload_id"]),
        "page_number": int(row["page_number"]),
        "source_row_number": int(row["source_row_number"]),
        "raw_sha256": str(row["raw_sha256"]),
        "capture_manifest_sha256": str(row["capture_manifest_sha256"]),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _blocked(reason: str) -> dict:
    return {
        "status": "BLOCKED", "rows": [], "errors": [{"reason": reason}],
        "row_count": 0, "all_rows_accepted": False,
        "backtest_admission_allowed": False, "production_enabled": False,
    }


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a timezone-aware ISO timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def ingest_captured_ohlcv_csv(
    *,
    capture_report: Mapping[str, object],
    manifest: Mapping[str, object],
    payloads: Mapping[str, bytes],
    column_map: Mapping[str, str],
    decision_cutoff: str,
) -> dict:
    """Ingest only the exact pages and manifest that produced a validated report."""
    required = {"symbol", "session_date", "open", "high", "low", "close", "volume"}
    if not isinstance(column_map, Mapping) or set(column_map) != required or len(set(column_map.values())) != len(column_map):
        raise ValueError("column_map must explicitly map each required field to a unique source column")
    if not isinstance(capture_report, Mapping) or not isinstance(manifest, Mapping):
        return _blocked("capture_report_or_manifest_invalid")
    if capture_report.get("status") != "CAPTURE_VALIDATED":
        return _blocked("capture_report_not_validated")

    try:
        cutoff = _aware(decision_cutoff, "decision_cutoff")
        available = _aware(manifest.get("available_at"), "manifest.available_at")
        digest = manifest_sha256(manifest)
    except (TypeError, ValueError):
        return _blocked("capture_manifest_or_cutoff_invalid")
    if available > cutoff:
        return _blocked("capture_not_available_by_decision_cutoff")
    if digest != capture_report.get("manifest_sha256"):
        return _blocked("manifest_does_not_match_validated_capture")
    for field in ("capture_id", "source_id", "publisher_id"):
        if not str(manifest.get(field, "")).strip() or str(manifest.get(field)) != str(capture_report.get(field)):
            return _blocked(f"{field}_does_not_match_validated_capture")

    pages = manifest.get("pages")
    proofs = capture_report.get("verified_pages")
    if not isinstance(pages, list) or not pages or not isinstance(proofs, list) or len(proofs) != len(pages):
        return _blocked("validated_page_set_does_not_match_manifest")
    proof_by_key, seen_proof_ids = {}, set()
    for proof in proofs:
        if not isinstance(proof, Mapping):
            return _blocked("invalid_validated_page_proof")
        key = (proof.get("page_number"), str(proof.get("payload_id", "")))
        if (isinstance(key[0], bool) or not isinstance(key[0], int) or key[0] < 1
                or not key[1] or key in proof_by_key or key[1] in seen_proof_ids
                or not isinstance(proof.get("raw_sha256"), str)
                or not _SHA256.fullmatch(proof["raw_sha256"])):
            return _blocked("duplicate_or_invalid_validated_page_proof")
        proof_by_key[key] = proof
        seen_proof_ids.add(key[1])

    rows, errors, seen = [], [], set()
    seen_manifest_pages, seen_manifest_ids = set(), set()
    ordered_pages = sorted(pages, key=lambda item: item.get("page_number", 0) if isinstance(item, Mapping) else 0)
    for page in ordered_pages:
        if not isinstance(page, Mapping):
            errors.append({"reason": "invalid_manifest_page"})
            continue
        page_no, payload_id = page.get("page_number"), str(page.get("payload_id", "")).strip()
        key = (page_no, payload_id)
        if (isinstance(page_no, bool) or not isinstance(page_no, int) or page_no < 1
                or not payload_id or key in seen_manifest_pages or payload_id in seen_manifest_ids):
            errors.append({"payload_id": payload_id or None, "reason": "duplicate_or_invalid_manifest_page"})
            continue
        seen_manifest_pages.add(key)
        seen_manifest_ids.add(payload_id)
        proof = proof_by_key.get(key)
        raw = payloads.get(payload_id)
        if proof is None or not isinstance(raw, bytes):
            errors.append({"payload_id": payload_id, "reason": "page_not_in_validated_capture_or_raw_bytes_missing"})
            continue
        actual = hashlib.sha256(raw).hexdigest()
        if actual != proof.get("raw_sha256") or actual != page.get("raw_sha256"):
            errors.append({"payload_id": payload_id, "reason": "page_hash_or_manifest_proof_mismatch"})
            continue

        try:
            decoded = raw.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)) or any(not header for header in headers):
                errors.append({"payload_id": payload_id, "reason": "duplicate_or_blank_csv_headers"})
                continue
            if any(column not in headers for column in column_map.values()):
                errors.append({"payload_id": payload_id, "reason": "required_source_column_missing"})
                continue
            for line_number, source_row in enumerate(reader, start=2):
                try:
                    if None in source_row or any(source_row.get(column) is None or not str(source_row[column]).strip()
                                                  for column in column_map.values()):
                        raise ValueError("CSV row has missing or extra fields")
                    symbol_raw = str(source_row[column_map["symbol"]])
                    symbol = symbol_raw.strip().upper()
                    if not symbol:
                        raise ValueError("blank symbol")
                    day_text = str(source_row[column_map["session_date"]]).strip()
                    day = date.fromisoformat(day_text)
                    if day.isoformat() != day_text:
                        raise ValueError("session date must be canonical YYYY-MM-DD")

                    prices = [float(source_row[column_map[field]]) for field in ("open", "high", "low", "close")]
                    opn, high, low, close = prices
                    volume_float = float(str(source_row[column_map["volume"]]).strip())
                    if not all(math.isfinite(value) for value in prices) or not math.isfinite(volume_float):
                        raise ValueError("OHLCV values must be finite")
                    if any(value <= 0 for value in prices) or not volume_float.is_integer() or volume_float <= 0:
                        raise ValueError("OHLC prices and whole-share volume must be positive")
                    volume = int(volume_float)
                    if low > min(opn, close) or high < max(opn, close) or high < low:
                        raise ValueError("OHLC geometry invalid")

                    key_row = (symbol, day_text)
                    if key_row in seen:
                        raise ValueError("duplicate symbol/session across capture pages")
                    seen.add(key_row)
                    row = {
                        "symbol": symbol, "session_date": day_text,
                        "open": opn, "high": high, "low": low, "close": close,
                        "volume": volume, "available_at": manifest["available_at"],
                        "source_id": str(capture_report["source_id"]),
                        "publisher_id": str(capture_report["publisher_id"]),
                        "capture_id": str(manifest["capture_id"]),
                        "payload_id": payload_id, "page_number": page_no,
                        "raw_sha256": actual, "source_row_number": line_number,
                        "capture_manifest_sha256": digest,
                    }
                    row["row_sha256"] = calculate_pilot_row_sha256(row)
                    rows.append(row)
                except (ValueError, TypeError, KeyError, OverflowError) as exc:
                    errors.append({"payload_id": payload_id, "line_number": line_number, "reason": str(exc)})
        except UnicodeDecodeError:
            errors.append({"payload_id": payload_id, "reason": "payload_not_utf8_csv"})

    if len(seen_manifest_pages) != len(proof_by_key) or seen_manifest_ids != seen_proof_ids:
        errors.append({"reason": "validated_page_set_not_consumed_exactly"})
    return {
        "status": "INGESTED" if rows and not errors else "BLOCKED",
        "row_count": len(rows), "rows": rows, "errors": errors,
        "all_rows_accepted": bool(rows) and not errors,
        "source_id": capture_report.get("source_id"),
        "publisher_id": capture_report.get("publisher_id"),
        "capture_id": manifest.get("capture_id"),
        "capture_manifest_sha256": digest,
        "source_bytes_unchanged": True,
        "backtest_admission_allowed": False,
        "production_enabled": False,
        "limitations": [
            "The manifest digest binds this ingestion to the exact structured capture manifest and page proofs.",
            "Row fingerprints bind normalized OHLCV to raw-payload locators; they do not authenticate the publisher.",
            "A syntactically valid capture does not establish official publisher authenticity or exchange completeness.",
            "Rows are normalized research candidates, not canonical market data.",
        ],
    }

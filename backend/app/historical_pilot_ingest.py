"""Normalize captured CSV OHLCV pages into provenance-preserving pilot rows.

No source access, column guessing, row repair or silent row dropping is performed.
The caller must supply the explicit schema mapping for the approved source.
"""
from __future__ import annotations
import csv
import hashlib
import io
from datetime import date, datetime
from typing import Mapping


def ingest_captured_ohlcv_csv(
    *,
    capture_report: Mapping[str, object],
    manifest: Mapping[str, object],
    payloads: Mapping[str, bytes],
    column_map: Mapping[str, str],
    decision_cutoff: str,
) -> dict:
    required = {"symbol", "session_date", "open", "high", "low", "close", "volume"}
    if set(column_map) != required or len(set(column_map.values())) != len(column_map):
        raise ValueError("column_map must explicitly map each required field to a unique source column")
    if capture_report.get("status") != "CAPTURE_VALIDATED":
        return {"status": "BLOCKED", "rows": [], "errors": [{"reason": "capture_report_not_validated"}], "row_count": 0}
    cutoff = datetime.fromisoformat(decision_cutoff.replace("Z", "+00:00"))
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("decision_cutoff must include timezone")
    available = datetime.fromisoformat(str(manifest.get("available_at")).replace("Z", "+00:00"))
    if available.tzinfo is None or available.utcoffset() is None or available > cutoff:
        return {"status": "BLOCKED", "rows": [], "errors": [{"reason": "capture_not_available_by_decision_cutoff"}], "row_count": 0}
    verified = {x["payload_id"]: x for x in capture_report.get("verified_pages", [])}
    rows, errors, seen = [], [], set()
    for page in sorted(manifest.get("pages", []), key=lambda x: x.get("page_number", 0)):
        payload_id = str(page.get("payload_id", ""))
        proof = verified.get(payload_id)
        raw = payloads.get(payload_id)
        if proof is None or not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != proof.get("raw_sha256"):
            errors.append({"payload_id": payload_id, "reason": "page_not_in_validated_capture_or_hash_changed"})
            continue
        try:
            decoded = raw.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
            headers = reader.fieldnames or []
            if any(column not in headers for column in column_map.values()):
                errors.append({"payload_id": payload_id, "reason": "required_source_column_missing"})
                continue
            for line_number, source_row in enumerate(reader, start=2):
                try:
                    symbol = str(source_row[column_map["symbol"]]).strip().upper()
                    day_text = str(source_row[column_map["session_date"]]).strip()
                    day = date.fromisoformat(day_text)
                    if day.isoformat() != day_text or not symbol:
                        raise ValueError("invalid symbol or noncanonical date")
                    opn, high, low, close = [float(source_row[column_map[k]]) for k in ("open", "high", "low", "close")]
                    volume_text = str(source_row[column_map["volume"]]).strip()
                    volume_float = float(volume_text)
                    if not volume_float.is_integer():
                        raise ValueError("fractional volume")
                    volume = int(volume_float)
                    if min(opn, high, low, close) <= 0 or low > min(opn, close) or high < max(opn, close) or volume < 0:
                        raise ValueError("OHLCV sanity failure")
                    key = (symbol, day_text)
                    if key in seen:
                        raise ValueError("duplicate symbol/session across capture pages")
                    seen.add(key)
                    rows.append({"symbol": symbol, "session_date": day_text, "open": opn, "high": high, "low": low, "close": close, "volume": volume, "available_at": manifest["available_at"], "source_id": capture_report.get("source_id"), "publisher_id": capture_report.get("publisher_id"), "capture_id": manifest.get("capture_id"), "payload_id": payload_id, "page_number": page.get("page_number"), "raw_sha256": proof["raw_sha256"], "source_row_number": line_number, "row_sha256": hashlib.sha256((symbol+"|"+day_text+"|"+repr((opn,high,low,close,volume))+"|"+proof["raw_sha256"]+"|"+str(line_number)).encode()).hexdigest()})
                except (ValueError, TypeError, KeyError, OverflowError) as exc:
                    errors.append({"payload_id": payload_id, "line_number": line_number, "reason": str(exc)})
        except UnicodeDecodeError:
            errors.append({"payload_id": payload_id, "reason": "payload_not_utf8_csv"})
    return {"status": "INGESTED" if rows and not errors else "BLOCKED", "row_count": len(rows), "rows": rows, "errors": errors, "all_rows_accepted": bool(rows) and not errors, "source_bytes_unchanged": True, "backtest_admission_allowed": False, "production_enabled": False, "limitations": ["Explicit column mapping is required; no schema inference occurs.", "A syntactically valid capture does not establish official publisher authenticity or exchange completeness.", "Rows are normalized research candidates, not canonical market data."]}

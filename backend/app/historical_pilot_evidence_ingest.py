"""Explicit-schema, provenance-preserving ingestion for non-OHLCV pilot evidence.

No source schema is guessed. Every dataset requires a caller-reviewed column map.
This module validates records and timestamps; it does not authenticate publishers.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
from datetime import date, datetime
from typing import Mapping

_SCHEMAS = {
    "official_market_calendar": {
        "required": {"session_date", "is_open", "session_type"},
        "dates": {"session_date"}, "booleans": {"is_open"},
        "keys": ("session_date",),
    },
    "official_security_master": {
        "required": {"symbol", "security_id", "effective_from", "listing_status"},
        "dates": {"effective_from", "effective_to"}, "booleans": set(),
        "keys": ("security_id", "effective_from"),
    },
    "official_corporate_actions": {
        "required": {"action_id", "symbol", "action_type", "announcement_at", "ex_date", "terms_reference"},
        "dates": {"ex_date", "record_date", "payment_date"}, "booleans": set(),
        "timestamps": {"announcement_at"}, "numbers": {"ratio_numerator", "ratio_denominator", "cash_amount"},
        "keys": ("action_id",),
    },
    "official_floorsheet": {
        "required": {"trade_id", "trade_timestamp", "session_date", "symbol", "quantity", "rate", "buyer_broker", "seller_broker"},
        "dates": {"session_date"}, "timestamps": {"trade_timestamp"},
        "numbers": {"quantity", "rate"}, "keys": ("trade_id",),
    },
    "cdsc_first_trade": {
        "required": {"symbol", "security_id", "first_trade_date", "evidence_reference"},
        "dates": {"first_trade_date"}, "keys": ("security_id",),
    },
    "official_sector_indices": {
        "required": {"sector", "session_date", "open", "high", "low", "close"},
        "dates": {"session_date"}, "numbers": {"open", "high", "low", "close", "volume"},
        "keys": ("sector", "session_date"),
    },
    "official_broker_trade_summary": {
        "required": {"session_date", "symbol", "broker_id", "buy_quantity", "sell_quantity", "buy_amount", "sell_amount"},
        "dates": {"session_date"}, "numbers": {"buy_quantity", "sell_quantity", "buy_amount", "sell_amount"},
        "keys": ("session_date", "symbol", "broker_id"),
    },
}


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp_must_be_timezone_aware")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp_must_be_timezone_aware")
    return parsed


def ingest_captured_evidence_csv(*, dataset_kind: str, package_report: Mapping[str, object],
                                 manifest: Mapping[str, object], payloads: Mapping[str, bytes],
                                 column_map: Mapping[str, str], decision_cutoff: str) -> dict:
    """Ingest one accepted capture package using an exact semantic-to-source map."""
    schema = _SCHEMAS.get(dataset_kind)
    if schema is None:
        raise ValueError("unsupported_non_ohlcv_dataset_kind")
    if package_report.get("status") != "CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION":
        return {"status":"BLOCKED","rows":[],"errors":[{"reason":"capture_package_not_accepted"}],
                "all_rows_accepted":False,"backtest_admission_allowed":False,"production_enabled":False}
    required = set(schema["required"])
    if not isinstance(column_map, Mapping) or not required.issubset(column_map):
        raise ValueError("column_map_must_cover_required_semantic_fields_with_unique_source_columns")
    mapped_columns = list(column_map.values())
    if (any(not isinstance(key, str) or not key.strip() for key in column_map)
            or any(not isinstance(value, str) or not value.strip() for value in mapped_columns)
            or len(set(mapped_columns)) != len(mapped_columns)):
        raise ValueError("column_map_must_cover_required_semantic_fields_with_unique_source_columns")
    try:
        cutoff = _aware(decision_cutoff)
        available = _aware(manifest.get("available_at"))
        if available > cutoff:
            raise ValueError("capture_available_after_decision_cutoff")
    except (TypeError, ValueError) as exc:
        return {"status":"BLOCKED","rows":[],"errors":[{"reason":str(exc)}],
                "all_rows_accepted":False,"backtest_admission_allowed":False,"production_enabled":False}
    if (manifest.get("capture_id") != package_report.get("capture_id")
            or manifest.get("source_id") != package_report.get("source_id")
            or manifest.get("publisher_id") != package_report.get("publisher_id")
            or package_report.get("manifest_sha256") is None):
        return {"status":"BLOCKED","rows":[],"errors":[{"reason":"manifest_package_identity_mismatch"}],
                "all_rows_accepted":False,"backtest_admission_allowed":False,"production_enabled":False}
    validation = package_report.get("validation_report", {})
    proofs = validation.get("verified_pages", []) if isinstance(validation, Mapping) else []
    pages = manifest.get("pages", [])
    if not isinstance(pages, list) or not pages or len(proofs) != len(pages):
        return {"status":"BLOCKED","rows":[],"errors":[{"reason":"verified_page_inventory_incomplete"}],
                "all_rows_accepted":False,"backtest_admission_allowed":False,"production_enabled":False}
    proof_map = {(p.get("page_number"), p.get("payload_id")):p for p in proofs if isinstance(p, Mapping)}
    rows, errors, seen = [], [], set()
    for page in pages:
        if not isinstance(page, Mapping):
            errors.append({"reason":"manifest_page_invalid"}); continue
        pid, page_no = page.get("payload_id"), page.get("page_number")
        raw = payloads.get(pid)
        proof = proof_map.get((page_no,pid))
        if not isinstance(raw,bytes) or not proof:
            errors.append({"payload_id":pid,"reason":"verified_raw_page_missing"}); continue
        digest = hashlib.sha256(raw).hexdigest()
        if digest != page.get("raw_sha256") or digest != proof.get("raw_sha256"):
            errors.append({"payload_id":pid,"reason":"raw_payload_hash_mismatch"}); continue
        try:
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)) or any(not h for h in headers):
                raise ValueError("duplicate_or_blank_csv_headers")
            if any(column_map[k] not in headers for k in required):
                raise ValueError("required_source_column_missing")
            for line_no, source in enumerate(reader, start=2):
                try:
                    if None in source or any(source.get(column_map[k]) is None or not str(source[column_map[k]]).strip() for k in required):
                        raise ValueError("row_has_missing_or_extra_fields")
                    row = {semantic:str(source[column]).strip() for semantic,column in column_map.items()}
                    for field in schema.get("dates", set()):
                        value=row.get(field)
                        if value not in (None,""):
                            parsed=date.fromisoformat(value)
                            if parsed.isoformat()!=value: raise ValueError(field+"_not_canonical_date")
                    for field in schema.get("timestamps", set()):
                        if row.get(field): _aware(row[field])
                    for field in schema.get("booleans", set()):
                        normalized=row[field].lower()
                        if normalized not in {"true","false","1","0","yes","no"}: raise ValueError(field+"_not_boolean")
                        row[field]=normalized in {"true","1","yes"}
                    for field in schema.get("numbers", set()):
                        if row.get(field) not in (None,""):
                            number=float(row[field])
                            if not math.isfinite(number) or number < 0: raise ValueError(field+"_must_be_finite_nonnegative")
                            row[field]=number
                    if dataset_kind == "official_sector_indices":
                        if row["low"] > min(row["open"],row["close"]) or row["high"] < max(row["open"],row["close"]) or row["high"] < row["low"]:
                            raise ValueError("sector_index_ohlc_geometry_invalid")
                    if dataset_kind == "official_floorsheet" and (row["quantity"] <= 0 or row["rate"] <= 0):
                        raise ValueError("floorsheet_quantity_and_rate_must_be_positive")
                    if dataset_kind == "official_corporate_actions" and row.get("ratio_denominator") not in (None,"") and float(row["ratio_denominator"]) <= 0:
                        raise ValueError("corporate_action_ratio_denominator_must_be_positive")
                    key=tuple(str(row.get(k,"")).upper() if k in {"symbol","sector","broker_id"} else str(row.get(k,"")) for k in schema["keys"])
                    if key in seen: raise ValueError("duplicate_dataset_business_key")
                    seen.add(key)
                    row.update({"dataset_kind":dataset_kind,"source_id":package_report["source_id"],
                        "publisher_id":package_report["publisher_id"],"capture_id":package_report["capture_id"],
                        "payload_id":pid,"page_number":page_no,"source_row_number":line_no,
                        "raw_sha256":digest,"available_at":manifest["available_at"]})
                    canonical=json.dumps(row,sort_keys=True,separators=(",",":"),default=str,allow_nan=False).encode()
                    row["row_sha256"]=hashlib.sha256(canonical).hexdigest()
                    rows.append(row)
                except (ValueError,TypeError,KeyError,OverflowError) as exc:
                    errors.append({"payload_id":pid,"line_number":line_no,"reason":str(exc)})
        except (UnicodeDecodeError, csv.Error) as exc:
            errors.append({"payload_id":pid,"reason":"csv_decode_or_parse_error:"+str(exc)})
    ok=bool(rows) and not errors
    return {"status":"INGESTED" if ok else "BLOCKED","dataset_kind":dataset_kind,
        "row_count":len(rows),"rows":rows,"errors":errors,"all_rows_accepted":ok,
        "source_bytes_unchanged":True,"publisher_authenticity_proven":False,
        "exchange_completeness_proven":False,"backtest_admission_allowed":False,"production_enabled":False,
        "limitations":["Explicit mappings are required; no source schema is inferred.",
          "Hashes preserve byte and row provenance but do not authenticate publishers.",
          "Empty or incomplete extracts are not accepted as proof of no events or no corporate actions."]}

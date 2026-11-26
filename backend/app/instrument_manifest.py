"""Evidence-backed active-universe manifest validation for NEPSE instruments."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date


TARGET_COUNTS = {"equity": 281, "mutual_fund": 47}
ACTIVE_STATUSES = {"active", "listed", "trading"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_iso_date(value: object) -> date:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        raise ValueError("date must use YYYY-MM-DD")
    return date.fromisoformat(value)


def validate_instrument_manifest(records: list[dict], *, as_of: str,
                                  require_primary_evidence: bool = True) -> dict:
    """Validate a supplied dated manifest; never synthesize missing instruments."""
    effective_date = _parse_iso_date(as_of)
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    errors, active, lifecycle = [], [], []
    required = (
        "security_id", "symbol", "instrument_type", "status",
        "valid_from", "evidence_id", "source_id",
    )
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append({"row": index, "error": "record_must_be_object"})
            continue
        missing = [
            key for key in required
            if not isinstance(row.get(key), str) or not row[key].strip()
        ]
        if missing:
            errors.append({"row": index, "error": "missing_or_invalid_required_fields", "fields": missing})
            continue
        if row["security_id"] != row["security_id"].strip():
            errors.append({"row": index, "error": "security_id_has_surrounding_whitespace"})
            continue
        if row["symbol"] != row["symbol"].strip() or row["symbol"] != row["symbol"].upper():
            errors.append({"row": index, "error": "symbol_must_be_trimmed_uppercase"})
            continue
        if row["instrument_type"] not in {
            "equity", "mutual_fund", "convertible_debenture",
            "non_convertible_debenture", "preference_share", "promoter_share", "other",
        }:
            errors.append({"row": index, "error": "unknown_instrument_type"})
            continue
        if row["status"].casefold() not in {
            "active", "listed", "trading", "suspended", "delisted", "inactive", "pending",
        }:
            errors.append({"row": index, "error": "unknown_lifecycle_status"})
            continue
        try:
            start = _parse_iso_date(row["valid_from"])
            end = _parse_iso_date(row["valid_to"]) if row.get("valid_to") is not None else None
        except ValueError:
            errors.append({"row": index, "error": "invalid_effective_date"})
            continue
        if end and end < start:
            errors.append({"row": index, "error": "reversed_effective_date"})
            continue
        lifecycle.append(row)
        if start <= effective_date and (end is None or effective_date <= end):
            if row["instrument_type"] in TARGET_COUNTS and row["status"].casefold() in ACTIVE_STATUSES:
                active.append(row)

    # Validate identity uniqueness across the complete dated lifecycle, not only
    # rows active on the requested as-of date. This catches historical overlaps
    # that could otherwise leak into point-in-time joins or price histories.
    overlapping_intervals = []
    dated = []
    for row_index, row in enumerate(lifecycle):
        start = date.fromisoformat(row["valid_from"])
        end = date.fromisoformat(row["valid_to"]) if row.get("valid_to") is not None else date.max
        dated.append((row_index, row, start, end))
    for index, (left_index, left, left_start, left_end) in enumerate(dated):
        for right_index, right, right_start, right_end in dated[index + 1:]:
            if left_start <= right_end and right_start <= left_end:
                same_id = left["security_id"] == right["security_id"]
                same_symbol = left["symbol"] == right["symbol"]
                if same_id or same_symbol:
                    overlapping_intervals.append({
                        "left_row": left_index,
                        "right_row": right_index,
                        "security_id": left["security_id"] if same_id else None,
                        "symbol": left["symbol"] if same_symbol else None,
                    })
    if overlapping_intervals:
        errors.append({
            "error": "overlapping_lifecycle_identity_intervals",
            "count": len(overlapping_intervals),
            "conflicts": overlapping_intervals,
        })

    ids = [r["security_id"] for r in active]
    symbols = [r["symbol"] for r in active]
    duplicate_ids = sorted(x for x, n in Counter(ids).items() if n > 1)
    duplicate_symbols = sorted(x for x, n in Counter(symbols).items() if n > 1)
    counts = dict(Counter(r["instrument_type"] for r in active))
    for kind, expected in TARGET_COUNTS.items():
        if counts.get(kind, 0) != expected:
            errors.append({"error": "target_count_mismatch", "instrument_type": kind,
                           "expected": expected, "observed": counts.get(kind, 0)})
    if duplicate_ids:
        errors.append({"error": "duplicate_active_security_ids", "values": duplicate_ids})
    if duplicate_symbols:
        errors.append({"error": "duplicate_active_symbols", "values": duplicate_symbols})
    if require_primary_evidence:
        non_primary = [r for r in active if r.get("source_tier") != "primary"]
        missing_source = [r for r in active if not isinstance(r.get("source_record_id"), str)
                          or not r["source_record_id"].strip()]
        if non_primary:
            errors.append({"error": "active_rows_lack_primary_source_tier", "count": len(non_primary)})
        if missing_source:
            errors.append({"error": "active_rows_lack_source_record_id", "count": len(missing_source)})
    return {
        "as_of": effective_date.isoformat(),
        "input_lifecycle_rows": len(records),
        "valid_lifecycle_rows": len(lifecycle),
        "active_target_rows": len(active),
        "active_counts_by_type": counts,
        "target_counts": TARGET_COUNTS,
        "duplicate_active_security_ids": duplicate_ids,
        "duplicate_active_symbols": duplicate_symbols,
        "overlapping_lifecycle_identity_intervals": overlapping_intervals,
        "errors": errors,
        "manifest_verified": not errors and len(active) == sum(TARGET_COUNTS.values()),
        "promotion_allowed": not errors and len(active) == sum(TARGET_COUNTS.values()),
        "policy": "dated_evidence_required_no_count_fabrication",
    }

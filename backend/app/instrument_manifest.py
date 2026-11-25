"""Evidence-backed active-universe manifest validation for NEPSE instruments."""
from __future__ import annotations

from collections import Counter
from datetime import date


TARGET_COUNTS = {"equity": 281, "mutual_fund": 47}
ACTIVE_STATUSES = {"active", "listed", "trading"}


def validate_instrument_manifest(records: list[dict], *, as_of: str,
                                  require_primary_evidence: bool = True) -> dict:
    """Validate a supplied dated manifest; never synthesize missing instruments."""
    effective_date = date.fromisoformat(as_of)
    errors, active, lifecycle = [], [], []
    for index, row in enumerate(records):
        required = ("security_id", "symbol", "instrument_type", "status",
                    "valid_from", "evidence_id", "source_id")
        missing = [key for key in required if not row.get(key)]
        if missing:
            errors.append({"row": index, "error": "missing_required_fields", "fields": missing})
            continue
        try:
            start = date.fromisoformat(row["valid_from"])
            end = date.fromisoformat(row["valid_to"]) if row.get("valid_to") else None
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

    ids = [r["security_id"] for r in active]
    symbols = [r["symbol"].strip().upper() for r in active]
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
        missing_source = [r for r in active if not r.get("source_record_id")]
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
        "errors": errors,
        "manifest_verified": not errors and len(active) == sum(TARGET_COUNTS.values()),
        "promotion_allowed": not errors and len(active) == sum(TARGET_COUNTS.values()),
        "policy": "dated_evidence_required_no_count_fabrication",
    }

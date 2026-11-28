"""Independent-source sector evidence reconciliation; never auto-resolves conflicts.

Evidence is evaluated as known at a decision timestamp and at an effective date.
Agreement is descriptive corroboration, not proof of official NEPSE classification.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from collections import defaultdict
from typing import Any
from zoneinfo import ZoneInfo

SOURCE_CLASSES = {"primary_nepse", "cdsc", "issuer", "secondary_publisher", "aggregator", "user_supplied", "unknown"}
PRIMARY_CLASSES = {"primary_nepse", "cdsc", "issuer"}


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_timezone_aware")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return result.astimezone(timezone.utc)


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}_must_be_iso_date") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field}_must_be_iso_date")
    return parsed


def reconcile_sector_evidence(observations: list[dict[str, Any]], *, symbols: list[str],
                              allowed_sector_codes: set[str], as_of_date: str,
                              decision_time: str) -> dict[str, Any]:
    """Return only independently corroborated sector mappings; conflicts are withheld."""
    effective_date = _date(as_of_date, "as_of_date")
    cutoff = _timestamp(decision_time, "decision_time")
    if effective_date > cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date():
        raise ValueError("as_of_date_after_decision_time")
    if not isinstance(symbols, list) or not symbols or any(not isinstance(s, str) or not s.strip() for s in symbols):
        raise ValueError("symbols_required")
    normalized_symbols = [s.strip().upper() for s in symbols]
    if len(normalized_symbols) != len(set(normalized_symbols)):
        raise ValueError("symbols_must_be_unique")
    if not isinstance(allowed_sector_codes, set) or not allowed_sector_codes:
        raise ValueError("allowed_sector_codes_required")
    if not isinstance(observations, list):
        raise ValueError("observations_must_be_list")

    visible = []
    for index, row in enumerate(observations):
        if not isinstance(row, dict):
            raise ValueError(f"observation_{index}_must_be_object")
        symbol, sector = row.get("symbol"), row.get("sector_code")
        source_id, publisher, source_class = row.get("source_id"), row.get("publisher_id"), row.get("source_class")
        if (not isinstance(symbol, str) or not symbol.strip()
                or not isinstance(sector, str) or sector not in allowed_sector_codes
                or not isinstance(source_id, str) or not source_id.strip()
                or not isinstance(publisher, str) or not publisher.strip()
                or source_class not in SOURCE_CLASSES):
            raise ValueError(f"observation_{index}_identity_or_class_invalid")
        payload_hash = row.get("payload_sha256")
        if (not isinstance(payload_hash, str) or len(payload_hash) != 64
                or any(c not in "0123456789abcdef" for c in payload_hash.lower())):
            raise ValueError(f"observation_{index}_payload_hash_invalid")
        record_ref = row.get("source_record_ref")
        if not isinstance(record_ref, str) or not record_ref.strip():
            raise ValueError(f"observation_{index}_source_record_ref_required")
        captured = _timestamp(row.get("captured_at"), f"observation_{index}_captured_at")
        available = _timestamp(row.get("available_at"), f"observation_{index}_available_at")
        start = _date(row.get("effective_from"), f"observation_{index}_effective_from")
        end = _date(row["effective_to"], f"observation_{index}_effective_to") if row.get("effective_to") else None
        if available < captured:
            raise ValueError(f"observation_{index}_available_before_capture")
        if end and end < start:
            raise ValueError(f"observation_{index}_effective_interval_reversed")
        if captured > cutoff or available > cutoff:
            continue
        if symbol.strip().upper() not in normalized_symbols:
            continue
        if start <= effective_date and (end is None or effective_date <= end):
            visible.append({
                "symbol": symbol.strip().upper(), "sector_code": sector,
                "source_id": source_id, "publisher_id": publisher.strip(),
                "source_class": source_class, "payload_sha256": payload_hash.lower(),
                "source_record_ref": record_ref.strip(),
            })

    by_symbol = defaultdict(list)
    for row in visible:
        by_symbol[row["symbol"]].append(row)
    results = {}
    for symbol in normalized_symbols:
        rows = by_symbol.get(symbol, [])
        sectors = defaultdict(dict)
        for row in rows:
            sectors[row["sector_code"]][row["publisher_id"]] = row
        if not rows:
            status, selected = "missing_evidence", None
        elif len(sectors) > 1:
            status, selected = "conflicting_sources", None
        else:
            sector, publishers = next(iter(sectors.items()))
            primary_publishers = {r["publisher_id"] for r in rows if r["source_class"] in PRIMARY_CLASSES}
            if len(publishers) < 2:
                status, selected = "single_source_only", None
            else:
                selected = sector
                status = "corroborated_primary" if primary_publishers else "corroborated_secondary"
        results[symbol] = {
            "status": status, "sector_code": selected, "source_count": len(rows),
            "independent_publisher_count": len({r["publisher_id"] for r in rows}),
            "primary_publisher_count": len({r["publisher_id"] for r in rows if r["source_class"] in PRIMARY_CLASSES}),
            "source_ids": sorted({r["source_id"] for r in rows}),
            "publishers": sorted({r["publisher_id"] for r in rows}),
            "evidence_refs": sorted({r["source_record_ref"] for r in rows}),
            "evidence_class": "point_in_time_independent_source_reconciliation",
            "official_membership_verified": False, "production_admission_allowed": False,
        }
    counts = defaultdict(int)
    for result in results.values():
        counts[result["status"]] += 1
    coverage = sum(result["sector_code"] is not None for result in results.values()) / len(results)
    return {
        "status": "review_ready" if coverage == 1.0 else "insufficient_evidence",
        "as_of_date": effective_date.isoformat(), "decision_time": cutoff.isoformat(),
        "symbol_count": len(results), "corroborated_coverage_pct": round(coverage * 100, 2),
        "status_counts": dict(sorted(counts.items())), "results": results,
        "verified": False, "admission_allowed": False, "production_recommendations_enabled": False,
        "limitations": [
            "Publisher agreement is corroboration, not proof of official NEPSE sector membership.",
            "Conflicting source claims are withheld rather than ranked or silently resolved.",
            "Evidence first available after decision_time is excluded to prevent look-ahead.",
        ],
    }

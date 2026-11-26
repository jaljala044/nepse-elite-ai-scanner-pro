"""Structural audit for point-in-time sector membership manifests.

This module checks consistency and provenance references only. It does not
authenticate a publisher, verify official NEPSE membership, or promote records.
A successful result is review_ready, never verified.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
from typing import Any
from zoneinfo import ZoneInfo

NEPAL_TZ = ZoneInfo("Asia/Kathmandu")


def _iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}_must_be_iso_date") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field}_must_be_iso_date")
    return parsed


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _digest(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value.lower()))


def manifest_digest(manifest: dict[str, Any]) -> str:
    """Return a stable digest of the supplied manifest excluding its own digest."""
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def audit_sector_membership_manifest(
    manifest: dict[str, Any],
    *,
    expected_symbols: list[str],
    allowed_sector_codes: set[str],
    decision_time: str,
    minimum_coverage: float = 1.0,
) -> dict[str, Any]:
    """Audit interval integrity and point-in-time coverage without promoting data."""
    cutoff = _utc(decision_time, "decision_time")
    if (isinstance(minimum_coverage, bool) or not isinstance(minimum_coverage, (int, float))
            or not 0 < minimum_coverage <= 1):
        raise ValueError("minimum_coverage_must_be_between_zero_and_one")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("unsupported_sector_membership_manifest_schema")
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ValueError("sector_membership_records_must_be_a_list")
    source_id = manifest.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("manifest_source_id_required")
    payload_digest = manifest.get("source_payload_sha256")
    if not _digest(payload_digest):
        raise ValueError("manifest_source_payload_sha256_invalid")
    captured_at = _utc(manifest.get("captured_at"), "captured_at")
    if captured_at > cutoff:
        raise ValueError("manifest_captured_after_decision_time")
    if manifest.get("manifest_sha256") != manifest_digest(manifest):
        raise ValueError("manifest_sha256_mismatch")
    if not isinstance(expected_symbols, list) or not expected_symbols:
        raise ValueError("expected_symbols_required")
    if any(not isinstance(item, str) or not item.strip() for item in expected_symbols):
        raise ValueError("expected_symbols_must_be_unique_nonempty")
    expected = [item.strip().upper() for item in expected_symbols]
    if len(expected) != len(set(expected)):
        raise ValueError("expected_symbols_must_be_unique_nonempty")
    if (not isinstance(allowed_sector_codes, set) or not allowed_sector_codes
            or any(not isinstance(code, str) or not code.strip() for code in allowed_sector_codes)):
        raise ValueError("allowed_sector_codes_required")

    normalized = []
    seen_ids = set()
    intervals: dict[str, list[tuple[date, date | None]]] = {}
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"membership_record_{index}_must_be_object")
        symbol = str(row.get("symbol", "")).strip().upper()
        sector = row.get("sector_code")
        record_id = row.get("record_id")
        if not symbol or not isinstance(sector, str) or sector not in allowed_sector_codes:
            raise ValueError(f"membership_record_{index}_invalid_identity")
        if not isinstance(record_id, str) or not record_id.strip() or record_id in seen_ids:
            raise ValueError(f"membership_record_{index}_invalid_or_duplicate_record_id")
        seen_ids.add(record_id)
        if row.get("source_id") != source_id:
            raise ValueError(f"membership_record_{index}_source_id_mismatch")
        if row.get("source_payload_sha256") != payload_digest:
            raise ValueError(f"membership_record_{index}_payload_digest_mismatch")
        source_ref = row.get("source_record_ref")
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError(f"membership_record_{index}_source_record_ref_required")
        start = _iso_date(row.get("effective_from"), f"membership_record_{index}_effective_from")
        end = (_iso_date(row.get("effective_to"), f"membership_record_{index}_effective_to")
               if row.get("effective_to") is not None else None)
        if end is not None and end < start:
            raise ValueError(f"membership_record_{index}_effective_interval_reversed")
        intervals.setdefault(symbol, []).append((start, end))
        normalized.append({"record_id": record_id, "symbol": symbol, "sector_code": sector,
                           "effective_from": start, "effective_to": end})

    for symbol, spans in intervals.items():
        ordered = sorted(spans, key=lambda item: item[0])
        for previous, current in zip(ordered, ordered[1:]):
            if previous[1] is None or current[0] <= previous[1]:
                raise ValueError(f"overlapping_effective_intervals:{symbol}")

    # NEPSE sessions and effective dates use Nepal local calendar dates.
    # Converting the cutoff to UTC first can shift an evening Nepal cutoff
    # into the previous UTC date and select the wrong membership snapshot.
    as_of = cutoff.astimezone(NEPAL_TZ).date()
    active: dict[str, list[str]] = {}
    for row in normalized:
        if row["effective_from"] <= as_of and (row["effective_to"] is None or as_of <= row["effective_to"]):
            active.setdefault(row["symbol"], []).append(row["sector_code"])
    ambiguous = sorted(symbol for symbol, values in active.items() if len(values) != 1)
    mapped = {symbol: values[0] for symbol, values in active.items() if len(values) == 1}
    missing = sorted(set(expected) - set(mapped))
    unexpected = sorted(set(mapped) - set(expected))
    coverage = len(set(expected) & set(mapped)) / len(expected)
    enough = coverage >= minimum_coverage and not ambiguous
    return {
        "status": "review_ready" if enough else "insufficient_evidence",
        "as_of_date": as_of.isoformat(),
        "expected_symbols": len(expected),
        "mapped_symbols": len(set(expected) & set(mapped)),
        "coverage_pct": round(coverage * 100, 2),
        "missing_symbols": missing,
        "unexpected_symbols": unexpected,
        "ambiguous_symbols": ambiguous,
        "membership": {symbol: mapped[symbol] for symbol in sorted(set(expected) & set(mapped))},
        "source_id": source_id,
        "source_payload_sha256": payload_digest.lower(),
        "manifest_sha256": manifest["manifest_sha256"],
        "captured_at": captured_at.isoformat(),
        "evidence_class": "structural_audit_only",
        "verified": False,
        "admission_allowed": False,
        "limitations": [
            "Structural consistency does not authenticate the source or establish official NEPSE membership.",
            "Independent source review, issuer identity checks and effective-date evidence remain mandatory.",
            "This result cannot be used as a verified membership artifact or production input.",
        ],
    }

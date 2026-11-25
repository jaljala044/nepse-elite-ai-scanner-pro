"""Immutable, evidence-backed validation for a target security-universe snapshot."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse

OFFICIAL_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "sebon.gov.np", "www.sebon.gov.np"}


def validate_universe_snapshot(snapshot: dict, *, expected_equities: int = 281,
                               expected_mutual_funds: int = 47) -> dict:
    """Validate provenance and exact target counts; never infer instrument type."""
    required = ("source_id", "source_url", "retrieved_at_utc",
                "raw_payload_sha256", "snapshot_as_of", "records")
    missing = [key for key in required if key not in snapshot or snapshot[key] in (None, "")]
    if missing:
        raise ValueError("universe snapshot missing required provenance: " + ", ".join(missing))
    parsed = urlparse(str(snapshot["source_url"]))
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise ValueError("universe source URL must be an approved official NEPSE or SEBON HTTPS host")
    digest = str(snapshot["raw_payload_sha256"]).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("raw_payload_sha256 must be a 64-character hex digest")
    try:
        snapshot_date = date.fromisoformat(str(snapshot["snapshot_as_of"]))
        retrieved = datetime.fromisoformat(str(snapshot["retrieved_at_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("snapshot_as_of or retrieved_at_utc has an invalid date/time format") from exc
    if retrieved.tzinfo is None or retrieved.utcoffset() != timezone.utc.utcoffset(retrieved):
        raise ValueError("retrieved_at_utc must include UTC timezone")
    if retrieved.date() < snapshot_date:
        raise ValueError("retrieval date cannot precede snapshot_as_of")
    records = snapshot["records"]
    if not isinstance(records, list) or not records:
        raise ValueError("universe records must be a non-empty list")
    seen_ids, seen_symbols = set(), set()
    target_counts = {"equity": 0, "mutual_fund": 0}
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"record {index}: expected object")
        security_id = str(row.get("security_id") or "").strip()
        symbol = str(row.get("symbol") or "").strip().upper()
        kind = row.get("instrument_type")
        status = row.get("status")
        target = row.get("target_in_scope")
        if not security_id or not symbol:
            raise ValueError(f"record {index}: security_id and symbol are required")
        if symbol != str(row.get("symbol") or "").strip():
            raise ValueError(f"record {index}: symbol must already be uppercase")
        if kind not in {"equity", "mutual_fund", "convertible_debenture",
                        "non_convertible_debenture", "preference_share", "other"}:
            raise ValueError(f"record {index}: unknown instrument_type {kind!r}")
        if status not in {"active", "suspended", "delisted", "inactive", "pending"}:
            raise ValueError(f"record {index}: unknown lifecycle status {status!r}")
        if not isinstance(target, bool):
            raise ValueError(f"record {index}: target_in_scope must be boolean")
        try:
            valid_from = date.fromisoformat(str(row["valid_from"]))
            valid_to = date.fromisoformat(str(row["valid_to"])) if row.get("valid_to") else None
        except (KeyError, ValueError) as exc:
            raise ValueError(f"record {index}: invalid effective lifecycle dates") from exc
        if valid_to is not None and valid_to < valid_from:
            raise ValueError(f"record {index}: valid_to precedes valid_from")
        if target:
            if status != "active" or kind not in target_counts:
                raise ValueError(f"record {index}: target universe allows only active equity/mutual_fund records")
            if not valid_from <= snapshot_date or (valid_to is not None and snapshot_date > valid_to):
                raise ValueError(f"record {index}: target record is not active on snapshot_as_of")
            if security_id in seen_ids or symbol in seen_symbols:
                raise ValueError(f"record {index}: duplicate target security_id or symbol")
            seen_ids.add(security_id)
            seen_symbols.add(symbol)
            target_counts[kind] += 1
    if target_counts["equity"] != expected_equities or target_counts["mutual_fund"] != expected_mutual_funds:
        raise ValueError(
            "target universe count mismatch: "
            f"equities={target_counts['equity']} (expected {expected_equities}), "
            f"mutual_funds={target_counts['mutual_fund']} (expected {expected_mutual_funds})"
        )
    return {
        "source_id": snapshot["source_id"],
        "source_url": snapshot["source_url"],
        "snapshot_as_of": snapshot_date.isoformat(),
        "retrieved_at_utc": retrieved.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "raw_payload_sha256": digest,
        "target_security_count": len(seen_ids),
        "target_equity_count": target_counts["equity"],
        "target_mutual_fund_count": target_counts["mutual_fund"],
        "manifest_verified": True,
        "promotion_allowed": False,
        "policy": "exact_counts_and_primary_provenance_required_no_ticker_guessing",
    }

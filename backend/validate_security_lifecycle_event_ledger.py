#!/usr/bin/env python3
"""Validate typed security lifecycle event evidence without inferring first trades."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

FIELDS = (
    "event_id", "security_id", "symbol", "event_type", "event_date",
    "evidence_tier", "source_url", "source_label", "review_status", "notes",
)
EVENT_TYPES = {
    "merger_joint_operations_start",
    "post_merger_shares_listed_and_trading_released",
    "post_merger_shares_listed",
    "original_listing_date",
    "trading_suspension_start",
    "trading_resumption",
    "delisting",
    "first_executed_trade",
}
EVIDENCE_TIERS = {
    "primary_nepse_notice",
    "secondary_notice",
    "secondary_nepse_listing_report",
    "secondary_company_metadata",
}
REVIEW_STATUSES = {
    "primary_notice_verified",
    "corroborated_not_exchange_primary",
    "secondary_metadata_only",
}


def _read(path: str | Path, fields: tuple[str, ...]) -> tuple[list[dict[str, str]], str]:
    raw = Path(path).read_bytes()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(fields) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("event ledger missing columns: " + ", ".join(sorted(missing)))
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    return rows, hashlib.sha256(raw).hexdigest()


def validate_security_lifecycle_event_ledger(
    ledger_path: str | Path,
    crosswalk_path: str | Path,
    expected_count: int | None = None,
) -> dict[str, Any]:
    rows, ledger_sha = _read(ledger_path, FIELDS)
    crosswalk, crosswalk_sha = _read(
        crosswalk_path, ("security_id", "symbol", "crosswalk_status")
    )
    active = {
        row["symbol"]: row["security_id"]
        for row in crosswalk
        if row.get("crosswalk_status") == "snapshot_id_match_active_status_A"
    }
    errors: list[str] = []
    seen_ids: set[str] = set()
    for line, row in enumerate(rows, 2):
        event_id = row["event_id"]
        symbol = row["symbol"].upper()
        if not event_id:
            errors.append(f"row_{line}:missing_event_id")
        elif event_id in seen_ids:
            errors.append(f"row_{line}:duplicate_event_id:{event_id}")
        seen_ids.add(event_id)
        if not symbol or not row["security_id"]:
            errors.append(f"row_{line}:missing_symbol_or_security_id")
        elif active.get(symbol) != row["security_id"]:
            errors.append(f"{symbol}:security_id_does_not_match_current_crosswalk")
        if row["event_type"] not in EVENT_TYPES:
            errors.append(f"{symbol}:unsupported_event_type:{row['event_type']}")
        try:
            date.fromisoformat(row["event_date"])
        except ValueError:
            errors.append(f"{symbol}:invalid_event_date")
        if row["evidence_tier"] not in EVIDENCE_TIERS:
            errors.append(f"{symbol}:unsupported_evidence_tier:{row['evidence_tier']}")
        if row["review_status"] not in REVIEW_STATUSES:
            errors.append(f"{symbol}:unsupported_review_status:{row['review_status']}")
        parsed = urlparse(row["source_url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{symbol}:invalid_source_url")
        if not row["source_label"] or not row["notes"]:
            errors.append(f"{symbol}:source_label_and_notes_required")
        if row["evidence_tier"] == "primary_nepse_notice" and row["review_status"] != "primary_notice_verified":
            errors.append(f"{symbol}:primary_notice_requires_primary_verified_status")
        if row["evidence_tier"] != "primary_nepse_notice" and row["review_status"] == "primary_notice_verified":
            errors.append(f"{symbol}:secondary_source_cannot_claim_primary_notice_verified")

    if expected_count is not None and len(rows) != expected_count:
        errors.append(f"event_count:{len(rows)}:expected:{expected_count}")

    return {
        "status": "valid_event_ledger_with_uncaptured_raw_sources" if not errors else "invalid",
        "promotion_allowed": False,
        "event_count": len(rows),
        "unique_event_ids": len(seen_ids),
        "event_type_counts": {
            kind: sum(1 for row in rows if row["event_type"] == kind)
            for kind in sorted({row["event_type"] for row in rows})
        },
        "evidence_tier_counts": {
            tier: sum(1 for row in rows if row["evidence_tier"] == tier)
            for tier in sorted({row["evidence_tier"] for row in rows})
        },
        "ledger_sha256": ledger_sha,
        "crosswalk_sha256": crosswalk_sha,
        "errors": errors,
        "limitations": [
            "Validation checks schema, current-snapshot identity, dates, URLs and evidence labels only.",
            "A listing or merger event does not prove first executed trade.",
            "Source URLs have not been archived as immutable raw payloads with retrieval timestamps and hashes.",
            "This validator does not authenticate the linked document contents or approve canonical promotion.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--crosswalk", required=True)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    report = validate_security_lifecycle_event_ledger(
        args.ledger, args.crosswalk, args.expected_count
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] != "invalid" else 1


if __name__ == "__main__":
    raise SystemExit(main())

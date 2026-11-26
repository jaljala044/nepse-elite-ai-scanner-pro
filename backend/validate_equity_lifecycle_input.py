#!/usr/bin/env python3
"""Validate dated equity lifecycle inputs against the approved current-ID crosswalk.

This validator checks provenance completeness and identity alignment only. It does
not infer listing dates, prove exchange sessions, or authorize canonical promotion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

FIELDS = (
    "security_id", "symbol", "instrument_type", "valid_from", "valid_to",
    "target_in_scope", "valid_from_evidence_status", "valid_from_evidence_uri",
    "valid_from_evidence_note",
)
STATUSES = {"verified_primary_notice", "verified_secondary_notice", "unverified"}


def _read(path: str | Path, required_fields: tuple[str, ...] = FIELDS) -> tuple[list[dict[str, str]], str]:
    raw = Path(path).read_bytes()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required_fields) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("lifecycle input missing columns: " + ", ".join(sorted(missing)))
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    return rows, hashlib.sha256(raw).hexdigest()


def validate_equity_lifecycle_input(
    lifecycle_path: str | Path,
    crosswalk_path: str | Path,
    expected_count: int = 281,
) -> dict[str, Any]:
    rows, lifecycle_sha = _read(lifecycle_path)
    crosswalk, crosswalk_sha = _read(crosswalk_path, ("security_id", "symbol", "crosswalk_status"))
    errors: list[str] = []
    expected = {
        row["symbol"]: row["security_id"]
        for row in crosswalk
        if row.get("crosswalk_status") == "snapshot_id_match_active_status_A"
    }
    if len(expected) != expected_count:
        errors.append(f"crosswalk_active_symbol_count:{len(expected)}:expected:{expected_count}")
    if len(rows) != expected_count:
        errors.append(f"lifecycle_row_count:{len(rows)}:expected:{expected_count}")

    seen_symbols: set[str] = set()
    seen_ids: set[str] = set()
    verified: list[str] = []
    unverified: list[str] = []
    for line, row in enumerate(rows, 2):
        symbol, security_id = row["symbol"].upper(), row["security_id"]
        if not symbol or not security_id:
            errors.append(f"row_{line}:missing_symbol_or_security_id")
            continue
        if symbol in seen_symbols:
            errors.append(f"row_{line}:duplicate_symbol:{symbol}")
        if security_id in seen_ids:
            errors.append(f"row_{line}:duplicate_security_id:{security_id}")
        seen_symbols.add(symbol)
        seen_ids.add(security_id)
        if row["instrument_type"] != "equity" or row["target_in_scope"].lower() != "true":
            errors.append(f"{symbol}:not_an_in_scope_equity")
        if expected.get(symbol) != security_id:
            errors.append(f"{symbol}:security_id_does_not_match_current_crosswalk")
        status = row["valid_from_evidence_status"]
        if status not in STATUSES:
            errors.append(f"{symbol}:unsupported_valid_from_evidence_status:{status}")
            continue
        start, end = row["valid_from"], row["valid_to"]
        if start:
            try:
                start_date = date.fromisoformat(start)
                end_date = date.fromisoformat(end) if end else None
                if end_date and end_date < start_date:
                    errors.append(f"{symbol}:valid_to_precedes_valid_from")
            except ValueError:
                errors.append(f"{symbol}:invalid_lifecycle_date")
        if status == "unverified":
            unverified.append(symbol)
            if start or row["valid_from_evidence_uri"]:
                errors.append(f"{symbol}:unverified_start_must_not_claim_date_or_evidence_uri")
            if not row["valid_from_evidence_note"]:
                errors.append(f"{symbol}:unverified_start_requires_explanation")
        else:
            verified.append(symbol)
            if not start or not row["valid_from_evidence_uri"] or not row["valid_from_evidence_note"]:
                errors.append(f"{symbol}:verified_start_requires_date_uri_and_note")

    missing_symbols = sorted(set(expected) - seen_symbols)
    extra_symbols = sorted(seen_symbols - set(expected))
    if missing_symbols:
        errors.append("missing_crosswalk_symbols:" + ",".join(missing_symbols))
    if extra_symbols:
        errors.append("symbols_not_in_crosswalk:" + ",".join(extra_symbols))

    return {
        "status": "valid_input_with_unverified_lifecycle" if not errors else "invalid",
        "promotion_allowed": False,
        "expected_equity_count": expected_count,
        "lifecycle_row_count": len(rows),
        "crosswalk_symbol_count": len(expected),
        "verified_start_count": len(verified),
        "verified_start_symbols": sorted(verified),
        "unverified_start_count": len(unverified),
        "unverified_start_symbols": sorted(unverified),
        "lifecycle_input_sha256": lifecycle_sha,
        "crosswalk_sha256": crosswalk_sha,
        "errors": errors,
        "limitations": [
            "Identity alignment is against the dated current security-ID snapshot only.",
            "A verified listing/trading-start source does not establish the complete lifecycle interval.",
            "This validation does not prove OHLCV completeness, official session coverage, or canonical promotion.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lifecycle", required=True)
    parser.add_argument("--crosswalk", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = validate_equity_lifecycle_input(args.lifecycle, args.crosswalk)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] != "invalid" else 1


if __name__ == "__main__":
    raise SystemExit(main())

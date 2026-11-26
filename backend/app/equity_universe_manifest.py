"""Validation for the versioned equity-only scanner universe manifest.

The current manifest is sourced from a secondary provider. Passing this validator
proves structural consistency and declared scope, not exchange-primary membership.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Iterable, Mapping

EXPECTED_SOURCE = "NepseAlpha"
EXPECTED_SOURCE_URL = "https://nepsealpha.com/traded-stocks/"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ISO_DATE_RE = re.compile(r"^\\d{4}-\\d{2}-\\d{2}$")


def validate_equity_manifest_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    expected_count: int = 281,
    expected_observed_on: str = "2026-11-26",
) -> dict:
    """Validate an equity-only manifest without inferring type from ticker text."""
    materialized = list(rows)
    if not materialized:
        raise ValueError("equity manifest must contain at least one record")
    if not isinstance(expected_count, int) or expected_count < 1:
        raise ValueError("expected_count must be a positive integer")
    if not isinstance(expected_observed_on, str) or not ISO_DATE_RE.fullmatch(expected_observed_on):
        raise ValueError("expected_observed_on must use YYYY-MM-DD")
    try:
        date.fromisoformat(expected_observed_on)
    except ValueError as exc:
        raise ValueError("expected_observed_on is not a valid date") from exc
    required = (
        "symbol", "security_id", "security_name", "sector", "instrument_type",
        "status", "observed_on", "source", "source_url", "source_snapshot_sha256",
    )
    symbols, security_ids = [], []
    snapshot_hashes = set()
    for index, row in enumerate(materialized):
        if not isinstance(row, Mapping):
            raise ValueError(f"record {index}: expected mapping")
        missing = [field for field in required if row.get(field) in (None, "")]
        if missing:
            raise ValueError(f"record {index}: missing required fields: {', '.join(missing)}")
        symbol = row["symbol"]
        security_id = row["security_id"]
        if not isinstance(symbol, str) or symbol != symbol.strip() or symbol != symbol.upper():
            raise ValueError(f"record {index}: symbol must be trimmed uppercase text")
        if not isinstance(security_id, str) or not security_id.isdigit():
            raise ValueError(f"record {index}: security_id must be a numeric string")
        if row["instrument_type"] != "Equity":
            raise ValueError(f"record {index}: scanner manifest accepts Equity only")
        if row["status"] != "Active":
            raise ValueError(f"record {index}: scanner manifest accepts Active records only")
        if row["observed_on"] != expected_observed_on:
            raise ValueError(f"record {index}: observed_on differs from manifest date")
        if row["source"] != EXPECTED_SOURCE or row["source_url"] != EXPECTED_SOURCE_URL:
            raise ValueError(f"record {index}: unexpected or mixed manifest source")
        digest = row["source_snapshot_sha256"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError(f"record {index}: invalid source_snapshot_sha256")
        symbols.append(symbol)
        security_ids.append(security_id)
        snapshot_hashes.add(digest)
    duplicate_symbols = sorted(k for k, v in Counter(symbols).items() if v > 1)
    duplicate_ids = sorted(k for k, v in Counter(security_ids).items() if v > 1)
    if duplicate_symbols:
        raise ValueError("duplicate symbols: " + ", ".join(duplicate_symbols))
    if duplicate_ids:
        raise ValueError("duplicate security_ids: " + ", ".join(duplicate_ids))
    if len(materialized) != expected_count:
        raise ValueError(f"equity count mismatch: {len(materialized)} (expected {expected_count})")
    if len(snapshot_hashes) != 1:
        raise ValueError("manifest rows do not share one source snapshot hash")
    return {
        "record_count": len(materialized),
        "unique_symbol_count": len(set(symbols)),
        "unique_security_id_count": len(set(security_ids)),
        "instrument_type": "Equity",
        "status": "Active",
        "observed_on": expected_observed_on,
        "source": EXPECTED_SOURCE,
        "source_snapshot_sha256": next(iter(snapshot_hashes)),
        "manifest_structurally_validated": True,
        "membership_authoritatively_verified": False,
        "promotion_allowed": False,
        "evidence_tier": "secondary_provider_snapshot",
        "policy": "equity_only_no_ticker_type_inference_no_secondary_source_promotion",
    }

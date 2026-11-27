"""Contract-level NEPSE first-trade evidence validator for the bounded pilot.

Secondary reports and archive boundaries are retained as context, never promoted
to exchange-verified execution. A contract match requires a raw response digest,
official source identity, contract identifier, exact date and sufficient quantity.
"""
from __future__ import annotations

import csv
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

FIELDS = (
    "security_id", "symbol", "reported_first_trade_date", "archive_first_row_date",
    "first_archive_row_volume", "prior_evidence_status", "official_floorsheet_status",
    "official_source_id", "official_source_url", "raw_response_sha256", "contract_id",
    "contract_date", "contract_quantity", "verified_at_utc", "notes",
)
STATUSES = {"pending_official_contract", "verified_contract_match", "conflict"}
OFFICIAL_SOURCE_ID = "NEPSE_OFFICIAL_FLOORSHEET"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_first_trade_floorsheet_evidence(
    rows: Iterable[Mapping[str, object]], *, expected_symbols: set[str] | None = None
) -> dict:
    materialized = list(rows)
    errors: list[str] = []
    seen: set[str] = set()
    verified: list[str] = []
    pending: list[str] = []
    conflicts: list[str] = []
    normalized = []

    for index, row in enumerate(materialized, 2):
        missing = [field for field in FIELDS if row.get(field) in (None, "")]
        # Evidence fields may be empty only while explicitly pending.
        required_base = FIELDS[:7] + ("notes",)
        missing_base = [field for field in required_base if row.get(field) in (None, "")]
        if missing_base:
            errors.append(f"row_{index}:missing_required_fields:{','.join(missing_base)}")
            continue

        symbol = row["symbol"]
        security_id = row["security_id"]
        if not isinstance(symbol, str) or symbol != symbol.strip() or symbol != symbol.upper():
            errors.append(f"row_{index}:invalid_symbol")
            continue
        if not isinstance(security_id, str) or not security_id.strip():
            errors.append(f"{symbol}:missing_security_id")
        if symbol in seen:
            errors.append(f"{symbol}:duplicate_symbol")
        seen.add(symbol)

        try:
            reported = date.fromisoformat(str(row["reported_first_trade_date"]))
            archive = date.fromisoformat(str(row["archive_first_row_date"]))
            volume = int(str(row["first_archive_row_volume"]))
            if volume <= 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(f"{symbol}:invalid_boundary_date_or_volume")
            continue

        status = row["official_floorsheet_status"]
        if status not in STATUSES:
            errors.append(f"{symbol}:unsupported_official_floorsheet_status:{status}")
            continue

        if status == "pending_official_contract":
            pending.append(symbol)
            if any(row.get(field) not in (None, "") for field in FIELDS[7:14]):
                errors.append(f"{symbol}:pending_record_must_not_claim_contract_evidence")
        elif status == "conflict":
            conflicts.append(symbol)
            if not row.get("notes"):
                errors.append(f"{symbol}:conflict_requires_explanation")
        else:
            source_id = row.get("official_source_id")
            source_url = row.get("official_source_url")
            digest = row.get("raw_response_sha256")
            contract_id = row.get("contract_id")
            contract_date = row.get("contract_date")
            contract_quantity = row.get("contract_quantity")
            verified_at = row.get("verified_at_utc")
            if source_id != OFFICIAL_SOURCE_ID:
                errors.append(f"{symbol}:contract_match_requires_official_nepse_source")
            if not isinstance(source_url, str) or not source_url.startswith("https://"):
                errors.append(f"{symbol}:contract_match_requires_https_source_url")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest.lower()):
                errors.append(f"{symbol}:contract_match_requires_raw_sha256")
            if not isinstance(contract_id, str) or not contract_id.strip():
                errors.append(f"{symbol}:contract_match_requires_contract_id")
            try:
                actual_date = date.fromisoformat(str(contract_date))
                quantity = int(str(contract_quantity))
                if actual_date != reported:
                    errors.append(f"{symbol}:contract_date_does_not_match_reported_first_trade")
                if quantity < volume:
                    errors.append(f"{symbol}:official_contract_quantity_below_archive_first_row_volume")
            except (ValueError, TypeError):
                errors.append(f"{symbol}:invalid_contract_date_or_quantity")
            try:
                timestamp = datetime.fromisoformat(str(verified_at).replace("Z", "+00:00"))
                if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
                    raise ValueError
            except ValueError:
                errors.append(f"{symbol}:verified_at_must_be_utc_iso_timestamp")
            if reported != archive:
                errors.append(f"{symbol}:reported_first_trade_and_archive_boundary_conflict")
            if not errors or not any(item.startswith(symbol + ":") for item in errors):
                verified.append(symbol)

        normalized.append({
            "security_id": security_id,
            "symbol": symbol,
            "reported_first_trade_date": reported.isoformat(),
            "archive_first_row_date": archive.isoformat(),
            "official_floorsheet_status": status,
        })

    if expected_symbols is not None:
        missing = sorted(expected_symbols - seen)
        extra = sorted(seen - expected_symbols)
        if missing:
            errors.append("missing_symbols:" + ",".join(missing))
        if extra:
            errors.append("unexpected_symbols:" + ",".join(extra))

    return {
        "status": "validated_with_unresolved_first_trade_evidence" if not errors else "invalid",
        "row_count": len(materialized),
        "verified_contract_match_count": len(verified),
        "verified_symbols": sorted(verified),
        "pending_count": len(pending),
        "pending_symbols": sorted(pending),
        "conflict_count": len(conflicts),
        "conflict_symbols": sorted(conflicts),
        "errors": errors,
        "exchange_execution_verified": bool(verified) and not errors,
        "canonical_lifecycle_promotion_allowed": False,
        "backtest_admission_allowed": False,
        "production_enabled": False,
        "rows": normalized,
        "limitations": [
            "Only contract-level official NEPSE evidence can satisfy the verified status.",
            "This validator does not fetch or authenticate source responses; raw capture and publisher verification remain external controls.",
            "Archive first-row volume and secondary reporting are not proof of an executed exchange contract.",
            "A contract match for one symbol does not establish complete historical session coverage.",
        ],
    }


def load_first_trade_evidence(path: str | Path, *, expected_symbols: set[str] | None = None) -> dict:
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return validate_first_trade_floorsheet_evidence(rows, expected_symbols=expected_symbols)

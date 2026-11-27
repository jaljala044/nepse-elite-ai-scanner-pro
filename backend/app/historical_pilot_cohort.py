"""Fail-closed audit for a bounded 2025 NEPSE lifecycle-start pilot cohort.

This validates a secondary-source research cohort and its observed archive boundary.
It deliberately does not certify exchange execution, calendar completeness, identity,
corporate actions, or eligibility for backtesting or production.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

REQUIRED_FIELDS = (
    "symbol",
    "reported_first_trade_date",
    "archive_first_row_date",
    "first_row_volume",
    "evidence_tier",
    "disposition",
    "evidence_basis",
    "notes",
)
EVIDENCE_TIER = "secondary_provider_plus_archive_observation"
CANDIDATE = "candidate_secondary_only"
QUARANTINED = "quarantined_boundary_mismatch"
ALLOWED_DISPOSITIONS = {CANDIDATE, QUARANTINED}


def _iso_date(value: object, field: str, symbol: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"{symbol}: {field} must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{symbol}: invalid {field}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{symbol}: {field} must use canonical ISO format")
    return parsed


def validate_lifecycle_pilot_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    expected_count: int = 18,
) -> dict:
    """Validate the cohort while keeping all rows research-only and non-promotable."""
    materialized = list(rows)
    if not isinstance(expected_count, int) or expected_count < 1:
        raise ValueError("expected_count must be a positive integer")
    if len(materialized) != expected_count:
        raise ValueError(f"cohort count mismatch: {len(materialized)} (expected {expected_count})")

    seen: set[str] = set()
    candidates = 0
    quarantined = 0
    normalized = []
    for index, row in enumerate(materialized):
        if not isinstance(row, Mapping):
            raise ValueError(f"row {index}: expected a mapping")
        missing = [field for field in REQUIRED_FIELDS if row.get(field) in (None, "")]
        if missing:
            raise ValueError(f"row {index}: missing fields: {', '.join(missing)}")

        symbol = row["symbol"]
        if not isinstance(symbol, str) or symbol != symbol.strip() or symbol != symbol.upper():
            raise ValueError(f"row {index}: symbol must be trimmed uppercase text")
        if symbol in seen:
            raise ValueError(f"duplicate symbol: {symbol}")
        seen.add(symbol)

        if row["evidence_tier"] != EVIDENCE_TIER:
            raise ValueError(f"{symbol}: unsupported evidence tier")
        disposition = row["disposition"]
        if disposition not in ALLOWED_DISPOSITIONS:
            raise ValueError(f"{symbol}: unsupported disposition")

        reported = _iso_date(row["reported_first_trade_date"], "reported_first_trade_date", symbol)
        archive = _iso_date(row["archive_first_row_date"], "archive_first_row_date", symbol)
        try:
            volume = int(str(row["first_row_volume"]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{symbol}: first_row_volume must be a positive integer") from exc
        if volume <= 0:
            raise ValueError(f"{symbol}: first_row_volume must be positive")
        if not isinstance(row["evidence_basis"], str) or not row["evidence_basis"].strip():
            raise ValueError(f"{symbol}: evidence_basis must be nonblank")

        if disposition == CANDIDATE:
            if reported != archive:
                raise ValueError(f"{symbol}: candidate dates disagree; quarantine the boundary")
            candidates += 1
        else:
            if reported == archive:
                raise ValueError(f"{symbol}: mismatch quarantine requires differing dates")
            quarantined += 1

        normalized.append({
            "symbol": symbol,
            "reported_first_trade_date": reported.isoformat(),
            "archive_first_row_date": archive.isoformat(),
            "first_row_volume": volume,
            "disposition": disposition,
        })

    return {
        "cohort_count": len(normalized),
        "candidate_count": candidates,
        "quarantined_count": quarantined,
        "symbols": sorted(seen),
        "rows": normalized,
        "status": "validated_for_bounded_research_review",
        "evidence_tier": EVIDENCE_TIER,
        "exchange_execution_verified": False,
        "canonical_promotion_allowed": False,
        "backtest_admission_allowed": False,
        "production_enabled": False,
        "limitations": [
            "Secondary/provider reports and archive first rows are not contract-level NEPSE execution proof.",
            "This cohort does not establish complete expected-session coverage or stable historical security IDs.",
            "Corporate-action price basis, floorsheet completeness, liquidity and source-row hashes require separate gates.",
            "A validated cohort structure is not an admitted price panel or a trading signal.",
        ],
    }


def load_lifecycle_pilot_cohort(path: str | Path) -> dict:
    """Load the committed CSV and return a non-promotable cohort audit."""
    cohort_path = Path(path)
    with cohort_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    result = validate_lifecycle_pilot_rows(rows)
    result["source_path"] = str(cohort_path)
    return result
